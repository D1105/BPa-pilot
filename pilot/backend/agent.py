"""
ИИ-агент для автоматизации продаж автомобилей
Использует LangGraph для управления диалогом и tools для поиска авто
"""
import os
import uuid
import json
import re
from typing import TypedDict
from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, ToolMessage
from langgraph.graph import StateGraph, END

from database import get_db, Lead, Conversation
from knowledge_base import get_relevant_knowledge
from car_tools import CAR_TOOLS, search_cars_in_db, CarSearchParams, format_cars_list_for_chat
from errors import (
    logger, 
    handle_openai_error, 
    with_retry, 
    get_fallback_response,
    AIServiceError,
    DatabaseError,
    ErrorContext,
)


class ConversationState(TypedDict):
    """Состояние диалога"""
    session_id: str
    messages: list
    extracted_data: dict
    current_stage: str  # greeting, discovery, qualification, closing
    missing_slots: list
    lead_qualification: str | None
    error: str | None  # Для отслеживания ошибок


class AutoImportAgent:
    """Агент для автоматизации продаж автомобилей"""
    
    SLOTS = [
        "car_brand",      # Марка авто
        "car_model",      # Модель
        "budget_min",     # Минимальный бюджет
        "budget_max",     # Максимальный бюджет
        "country",        # Страна-источник
        "timeline",       # Сроки покупки
        "body_type",      # Тип кузова
        "name",           # Имя клиента
        "phone",          # Телефон
    ]
    
    REQUIRED_FOR_QUALIFICATION = ["car_brand", "budget_max"]
    REQUIRED_FOR_CLOSING = ["name", "phone"]
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0.7,
            base_url=os.getenv("OPENAI_BASE_URL"),
            timeout=30.0,  # Таймаут запроса
            max_retries=0,  # Отключаем встроенные retry, используем свои
        )
        # LLM с привязанными tools для поиска авто
        self.llm_with_tools = self.llm.bind_tools(CAR_TOOLS)
        self.graph = self._build_graph()
        self.error_context = ErrorContext()
    
    def _build_graph(self) -> StateGraph:
        """Построение графа диалога"""
        workflow = StateGraph(ConversationState)
        
        # Добавляем узлы
        workflow.add_node("extract_slots", self._extract_slots)
        workflow.add_node("determine_stage", self._determine_stage)
        workflow.add_node("generate_response", self._generate_response)
        workflow.add_node("save_to_db", self._save_to_db)
        
        # Определяем переходы
        workflow.set_entry_point("extract_slots")
        workflow.add_edge("extract_slots", "determine_stage")
        workflow.add_edge("determine_stage", "generate_response")
        workflow.add_edge("generate_response", "save_to_db")
        workflow.add_edge("save_to_db", END)
        
        return workflow.compile()
    
    @with_retry(max_retries=3, base_delay=1.0)
    async def _call_llm(self, messages: list) -> str:
        """Вызов LLM с retry логикой"""
        response = await self.llm.ainvoke(messages)
        return response.content
    
    async def _extract_slots(self, state: ConversationState) -> ConversationState:
        """Извлечение параметров из сообщения пользователя"""
        last_message = state["messages"][-1]["content"] if state["messages"] else ""
        
        extraction_prompt = f"""Извлеки информацию из сообщения клиента об автомобиле.
        
Сообщение: "{last_message}"

Текущие известные данные: {json.dumps(state["extracted_data"], ensure_ascii=False)}

Извлеки и верни JSON с полями (только если информация явно указана):
- car_brand: марка автомобиля (Toyota, BMW, Hyundai и т.д.)
- car_model: модель (Camry, X5, Tucson и т.д.)
- budget_min: минимальный бюджет в рублях (число)
- budget_max: максимальный бюджет в рублях (число)
- country: страна-источник (Корея, Япония, Германия, США, Китай)
- timeline: сроки покупки (срочно, 1-2 месяца, не спешу и т.д.)
- body_type: тип кузова (седан, кроссовер, внедорожник, хэтчбек)
- name: имя клиента
- phone: телефон клиента

Верни ТОЛЬКО валидный JSON без markdown-разметки. Для неизвестных полей используй null."""

        try:
            response = await self._call_llm([
                SystemMessage(content="Ты - система извлечения данных. Отвечай только JSON."),
                HumanMessage(content=extraction_prompt)
            ])
            
            # Парсим JSON из ответа
            json_str = response.strip()
            # Убираем возможную markdown-разметку
            json_str = re.sub(r'^```json\s*', '', json_str)
            json_str = re.sub(r'\s*```$', '', json_str)
            
            extracted = json.loads(json_str)
            
            # Обновляем extracted_data, сохраняя предыдущие значения
            for key, value in extracted.items():
                if value is not None:
                    # Конвертируем бюджет в числа
                    if key in ["budget_min", "budget_max"] and isinstance(value, str):
                        value = self._parse_budget(value)
                    state["extracted_data"][key] = value
            
            logger.debug(f"Extracted data: {state['extracted_data']}")
                    
        except AIServiceError as e:
            # Ошибка AI-сервиса — продолжаем без извлечения
            logger.warning(f"Slot extraction failed: {e.message}")
            state["error"] = e.user_message
        except json.JSONDecodeError as e:
            # Ошибка парсинга JSON — не критично
            logger.warning(f"JSON parsing error in extraction: {e}")
        except Exception as e:
            logger.error(f"Unexpected extraction error: {e}")
        
        # Определяем недостающие слоты
        state["missing_slots"] = [
            slot for slot in self.SLOTS 
            if state["extracted_data"].get(slot) is None
        ]
        
        return state
    
    def _parse_budget(self, value) -> int | None:
        """Парсинг бюджета из различных форматов"""
        if isinstance(value, (int, float)):
            return int(value)
        
        if isinstance(value, str):
            # Убираем пробелы и приводим к нижнему регистру
            value = value.lower().replace(" ", "").replace(",", ".")
            
            # Ищем число
            numbers = re.findall(r'[\d.]+', value)
            if not numbers:
                return None
            
            num = float(numbers[0])
            
            # Определяем множитель
            if 'млн' in value or 'миллион' in value:
                return int(num * 1_000_000)
            elif 'тыс' in value or 'тысяч' in value:
                return int(num * 1_000)
            elif num < 100:  # Вероятно, это миллионы
                return int(num * 1_000_000)
            else:
                return int(num)
        
        return None
    
    async def _determine_stage(self, state: ConversationState) -> ConversationState:
        """Определение этапа диалога"""
        data = state["extracted_data"]
        
        # Проверяем наличие обязательных полей для каждого этапа
        has_basic_info = any([
            data.get("car_brand"),
            data.get("budget_max"),
            data.get("body_type"),
        ])
        
        has_qualification_info = all([
            data.get(slot) for slot in self.REQUIRED_FOR_QUALIFICATION
        ])
        
        has_contact_info = all([
            data.get(slot) for slot in self.REQUIRED_FOR_CLOSING
        ])
        
        # Определяем квалификацию лида
        if has_contact_info and has_qualification_info:
            budget = data.get("budget_max", 0)
            timeline = data.get("timeline", "").lower()
            
            if budget >= 3_000_000 or "срочно" in timeline or "быстр" in timeline:
                state["lead_qualification"] = "hot"
            elif budget >= 1_500_000 or has_basic_info:
                state["lead_qualification"] = "warm"
            else:
                state["lead_qualification"] = "cold"
        
        # Определяем этап
        if not has_basic_info:
            state["current_stage"] = "discovery"
        elif not has_qualification_info:
            state["current_stage"] = "qualification"
        elif not has_contact_info:
            state["current_stage"] = "closing"
        else:
            state["current_stage"] = "completed"
        
        return state
    
    async def _generate_response(self, state: ConversationState) -> ConversationState:
        """Генерация ответа агента с поддержкой tool-calling"""
        
        # Проверяем, нужно ли использовать fallback
        if self.error_context.should_use_fallback():
            logger.warning("Using fallback response due to consecutive errors")
            state["messages"].append({
                "role": "assistant",
                "content": get_fallback_response("general")
            })
            return state
        
        # Получаем релевантные знания из базы
        last_message = state["messages"][-1]["content"] if state["messages"] else ""
        knowledge = get_relevant_knowledge(last_message)
        
        system_prompt = f"""Ты — ИИ-консультант компании "АвтоИмпорт Pro". Помогаешь клиентам подобрать и заказать автомобиль из-за рубежа.

ТВОЯ ЗАДАЧА:
1. Выяснить потребности клиента (марка, модель, бюджет, сроки)
2. Проконсультировать по процессу импорта
3. ПОКАЗАТЬ РЕАЛЬНЫЕ АВТОМОБИЛИ из каталога используя инструмент search_cars
4. Получить контактные данные для связи менеджера

ТЕКУЩИЙ ЭТАП: {state["current_stage"]}
ИЗВЕСТНЫЕ ДАННЫЕ О КЛИЕНТЕ: {json.dumps(state["extracted_data"], ensure_ascii=False, indent=2)}
НЕДОСТАЮЩАЯ ИНФОРМАЦИЯ: {', '.join(state["missing_slots"][:3]) if state["missing_slots"] else 'всё известно'}

БАЗА ЗНАНИЙ:
{knowledge}

ИНСТРУМЕНТЫ:
У тебя есть доступ к каталогу автомобилей. ОБЯЗАТЕЛЬНО используй инструменты когда:
- Клиент спрашивает о наличии конкретных авто
- Клиент интересуется ценами
- Клиент хочет посмотреть варианты
- Известны марка, бюджет или другие параметры для поиска

Доступные инструменты:
- search_cars: поиск авто по фильтрам (марка, модель, цена, год, страна, тип кузова)
- get_available_brands: список марок в наличии
- get_price_range: диапазон цен на марку/модель

ПРАВИЛА ОБЩЕНИЯ:
- Будь дружелюбным и профессиональным
- Отвечай кратко, но информативно (2-4 предложения)
- Задавай по одному уточняющему вопросу за раз
- Используй эмодзи умеренно (1-2 на сообщение)
- Если клиент готов — попроси контакты для связи менеджера
- На этапе closing обязательно запроси имя и телефон
- ВСЕГДА показывай реальные авто из каталога когда это уместно!

ЭТАПЫ ДИАЛОГА:
- discovery: выясняем базовые потребности (марка, тип кузова, бюджет)
- qualification: уточняем детали (страна, сроки, конкретная модель)  
- closing: получаем контакты (имя, телефон)
- completed: благодарим и подтверждаем, что менеджер свяжется"""

        messages = [SystemMessage(content=system_prompt)]
        
        # Добавляем историю диалога
        for msg in state["messages"]:
            if msg["role"] == "user":
                messages.append(HumanMessage(content=msg["content"]))
            else:
                messages.append(AIMessage(content=msg["content"]))
        
        try:
            # Первый вызов — может вернуть tool_calls
            response = await self.llm_with_tools.ainvoke(messages)
            
            # Обрабатываем tool calls если есть
            if response.tool_calls:
                logger.info(f"Tool calls detected: {[tc['name'] for tc in response.tool_calls]}")
                
                # Добавляем ответ с tool_calls в историю
                messages.append(response)
                
                # Выполняем каждый tool call
                for tool_call in response.tool_calls:
                    tool_result = await self._execute_tool(tool_call)
                    messages.append(ToolMessage(
                        content=tool_result,
                        tool_call_id=tool_call["id"]
                    ))
                
                # Второй вызов — генерируем финальный ответ с результатами tools
                final_response = await self.llm_with_tools.ainvoke(messages)
                response_content = final_response.content
            else:
                response_content = response.content
            
            self.error_context.record_success()
            
            # Добавляем ответ в историю
            state["messages"].append({
                "role": "assistant",
                "content": response_content
            })
            
        except AIServiceError as e:
            self.error_context.record_error()
            logger.error(f"Response generation failed: {e.message}")
            
            # Используем fallback ответ
            state["messages"].append({
                "role": "assistant",
                "content": e.user_message
            })
            state["error"] = e.user_message
        except Exception as e:
            self.error_context.record_error()
            logger.error(f"Unexpected error in response generation: {e}")
            
            state["messages"].append({
                "role": "assistant",
                "content": get_fallback_response("general")
            })
            state["error"] = str(e)
        
        return state
    
    async def _execute_tool(self, tool_call: dict) -> str:
        """Выполнение tool call"""
        tool_name = tool_call["name"]
        tool_args = tool_call["args"]
        
        logger.info(f"Executing tool: {tool_name} with args: {tool_args}")
        
        try:
            if tool_name == "search_cars":
                params = CarSearchParams(**tool_args)
                cars = await search_cars_in_db(params)
                return format_cars_list_for_chat(cars)
            
            elif tool_name == "get_available_brands":
                from car_tools import get_available_brands
                return await get_available_brands.ainvoke({})
            
            elif tool_name == "get_price_range":
                from car_tools import get_price_range
                return await get_price_range.ainvoke(tool_args)
            
            else:
                return f"Неизвестный инструмент: {tool_name}"
                
        except Exception as e:
            logger.error(f"Tool execution error: {e}")
            return f"Ошибка при выполнении поиска: {str(e)}"
    
    async def _save_to_db(self, state: ConversationState) -> ConversationState:
        """Сохранение данных в БД с обработкой ошибок"""
        try:
            async with get_db() as db:
                from sqlalchemy import select
                
                # Ищем или создаём лид
                result = await db.execute(
                    select(Lead).where(Lead.session_id == state["session_id"])
                )
                lead = result.scalar_one_or_none()
                
                if not lead:
                    lead = Lead(session_id=state["session_id"])
                    db.add(lead)
                
                # Обновляем данные лида
                data = state["extracted_data"]
                lead.name = data.get("name") or lead.name
                lead.phone = data.get("phone") or lead.phone
                lead.car_brand = data.get("car_brand") or lead.car_brand
                lead.car_model = data.get("car_model") or lead.car_model
                lead.budget_min = data.get("budget_min") or lead.budget_min
                lead.budget_max = data.get("budget_max") or lead.budget_max
                lead.country = data.get("country") or lead.country
                lead.timeline = data.get("timeline") or lead.timeline
                lead.body_type = data.get("body_type") or lead.body_type
                lead.qualification = state["lead_qualification"] or lead.qualification
                lead.status = "qualified" if state["current_stage"] == "completed" else "in_progress"
                lead.updated_at = datetime.utcnow()
                
                # Сохраняем последние сообщения
                for msg in state["messages"][-2:]:  # Последние 2 сообщения (user + assistant)
                    conv = Conversation(
                        session_id=state["session_id"],
                        role=msg["role"],
                        content=msg["content"]
                    )
                    db.add(conv)
                
                await db.commit()
                logger.debug(f"Saved data for session {state['session_id']}")
                
        except Exception as e:
            # Ошибка БД не должна ломать ответ пользователю
            logger.error(f"Database save error: {e}")
            # Не прокидываем ошибку — ответ уже сгенерирован
        
        return state
    
    async def process_message(
        self,
        message: str,
        history: list[dict],
        session_id: str | None = None,
    ) -> dict:
        """Обработка сообщения от пользователя"""
        
        if not session_id:
            session_id = str(uuid.uuid4())[:8]
        
        logger.info(f"Processing message for session {session_id}")
        
        # Валидация входных данных
        if not message or not message.strip():
            return {
                "response": "Пожалуйста, напишите ваш вопрос.",
                "session_id": session_id,
                "extracted_data": {},
                "lead_status": "discovery",
                "qualification": None,
            }
        
        # Ограничение длины сообщения
        if len(message) > 2000:
            message = message[:2000] + "..."
            logger.warning(f"Message truncated for session {session_id}")
        
        # Загружаем предыдущие данные из БД если есть
        extracted_data = {}
        try:
            async with get_db() as db:
                from sqlalchemy import select
                result = await db.execute(
                    select(Lead).where(Lead.session_id == session_id)
                )
                lead = result.scalar_one_or_none()
                if lead:
                    extracted_data = {
                        "name": lead.name,
                        "phone": lead.phone,
                        "car_brand": lead.car_brand,
                        "car_model": lead.car_model,
                        "budget_min": lead.budget_min,
                        "budget_max": lead.budget_max,
                        "country": lead.country,
                        "timeline": lead.timeline,
                        "body_type": lead.body_type,
                    }
                    # Убираем None значения
                    extracted_data = {k: v for k, v in extracted_data.items() if v is not None}
        except Exception as e:
            logger.error(f"Error loading lead data: {e}")
            # Продолжаем без предыдущих данных
        
        # Формируем начальное состояние
        initial_state: ConversationState = {
            "session_id": session_id,
            "messages": history + [{"role": "user", "content": message}],
            "extracted_data": extracted_data,
            "current_stage": "discovery",
            "missing_slots": self.SLOTS.copy(),
            "lead_qualification": None,
            "error": None,
        }
        
        try:
            # Запускаем граф
            final_state = await self.graph.ainvoke(initial_state)
            
            # Возвращаем результат
            return {
                "response": final_state["messages"][-1]["content"],
                "session_id": session_id,
                "extracted_data": final_state["extracted_data"],
                "lead_status": final_state["current_stage"],
                "qualification": final_state["lead_qualification"],
                "error": final_state.get("error"),
            }
            
        except AIServiceError as e:
            logger.error(f"AI service error: {e.message}")
            return {
                "response": e.user_message,
                "session_id": session_id,
                "extracted_data": extracted_data,
                "lead_status": "error",
                "qualification": None,
                "error": e.user_message,
            }
        except Exception as e:
            logger.error(f"Unexpected error in process_message: {e}")
            return {
                "response": get_fallback_response("general"),
                "session_id": session_id,
                "extracted_data": extracted_data,
                "lead_status": "error",
                "qualification": None,
                "error": str(e),
            }
