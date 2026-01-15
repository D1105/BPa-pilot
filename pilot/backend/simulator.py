"""
Симулятор клиента для тренировки менеджеров по продажам
ИИ играет роль покупателя с настраиваемым характером
"""
import os
import uuid
import json
import re
from typing import TypedDict
from pydantic import BaseModel
from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

from errors import (
    logger,
    handle_openai_error,
    with_retry,
    get_fallback_response,
    AIServiceError,
    ErrorContext,
)


class ClientPersona(BaseModel):
    """Настройки персонажа клиента"""
    # Основные параметры (1-10)
    cooperativeness: int = 5      # Сговорчивость (1=упёртый, 10=легко соглашается)
    rudeness: int = 3             # Грубость (1=вежливый, 10=хам)
    budget_flexibility: int = 5   # Гибкость бюджета (1=жёсткий лимит, 10=готов переплатить)
    urgency: int = 5              # Срочность (1=не спешит, 10=нужно вчера)
    knowledge_level: int = 5      # Знание рынка (1=новичок, 10=эксперт)
    decisiveness: int = 5         # Решительность (1=долго думает, 10=быстро решает)
    trust_level: int = 5          # Доверие к продавцу (1=подозрительный, 10=доверяет)
    
    # Сценарий клиента
    desired_car: str = "кроссовер"
    budget_range: str = "2-3 млн рублей"
    country_preference: str = "Корея или Япония"
    timeline: str = "в течение 2 месяцев"
    
    # Скрытые возражения (менеджер должен их выявить)
    hidden_objections: list[str] = [
        "боюсь что обманут с пробегом",
        "жена против покупки из-за рубежа"
    ]
    
    # Триггеры для покупки
    buying_triggers: list[str] = [
        "гарантия на скрытые дефекты",
        "возможность проверки перед покупкой"
    ]


class SimulationState(TypedDict):
    """Состояние симуляции"""
    session_id: str
    persona: dict
    messages: list
    manager_score: int  # Оценка работы менеджера (0-100)
    feedback_points: list[str]  # Заметки для фидбека
    is_deal_closed: bool
    objections_handled: list[str]
    triggers_activated: list[str]


class ClientSimulator:
    """Симулятор клиента для тренировки продажников"""
    
    PERSONA_PRESETS = {
        "easy": ClientPersona(
            cooperativeness=8,
            rudeness=2,
            budget_flexibility=7,
            urgency=7,
            knowledge_level=3,
            decisiveness=7,
            trust_level=7,
            desired_car="Hyundai Tucson",
            budget_range="2.5-3 млн рублей",
            hidden_objections=["немного переживаю за сроки доставки"],
            buying_triggers=["быстрая доставка", "хорошие отзывы"]
        ),
        "medium": ClientPersona(
            cooperativeness=5,
            rudeness=4,
            budget_flexibility=5,
            urgency=5,
            knowledge_level=5,
            decisiveness=5,
            trust_level=5,
            desired_car="Toyota RAV4 или Camry",
            budget_range="2-2.5 млн рублей",
            hidden_objections=[
                "боюсь что обманут с пробегом",
                "не уверен в качестве растаможки"
            ],
            buying_triggers=["гарантия", "прозрачная история авто"]
        ),
        "hard": ClientPersona(
            cooperativeness=3,
            rudeness=6,
            budget_flexibility=3,
            urgency=3,
            knowledge_level=8,
            decisiveness=3,
            trust_level=3,
            desired_car="BMW X5 или Mercedes GLE",
            budget_range="4-5 млн рублей, но хочу дешевле",
            country_preference="только Германия, оригинал",
            hidden_objections=[
                "уже обжёгся с перекупами",
                "жена категорически против",
                "друг сказал что это развод"
            ],
            buying_triggers=[
                "личная встреча и детальный договор",
                "возможность отказаться на любом этапе",
                "рекомендации от реальных клиентов"
            ]
        ),
        "nightmare": ClientPersona(
            cooperativeness=1,
            rudeness=9,
            budget_flexibility=1,
            urgency=2,
            knowledge_level=9,
            decisiveness=2,
            trust_level=1,
            desired_car="Porsche Cayenne",
            budget_range="хочу за 3 млн, хотя знаю что стоит 6",
            country_preference="США, но без битья",
            timeline="когда-нибудь, не тороплюсь",
            hidden_objections=[
                "вообще не собираюсь покупать, просто узнаю цены",
                "у меня 10 знакомых перекупов",
                "вы все мошенники"
            ],
            buying_triggers=[
                "только если будет в 2 раза дешевле рынка"
            ]
        )
    }
    
    def __init__(self):
        self.llm = ChatOpenAI(
            model=os.getenv("OPENAI_MODEL", "gpt-4o-mini"),
            temperature=0.8,  # Больше вариативности для реалистичности
            base_url=os.getenv("OPENAI_BASE_URL"),
            timeout=30.0,
            max_retries=0,
        )
        self.error_context = ErrorContext()
    
    def _build_system_prompt(self, persona: ClientPersona) -> str:
        """Создание системного промпта для персонажа клиента"""
        
        rudeness_desc = {
            1: "очень вежливый и культурный",
            2: "вежливый",
            3: "нейтрально-вежливый", 
            4: "немного резкий",
            5: "прямолинейный",
            6: "грубоватый",
            7: "грубый",
            8: "хамоватый",
            9: "откровенный хам",
            10: "агрессивный и оскорбительный"
        }
        
        coop_desc = {
            1: "крайне упёртый, не идёт на компромиссы",
            2: "очень сложный в переговорах",
            3: "скептичный, много сомневается",
            4: "осторожный",
            5: "нейтральный",
            6: "достаточно открытый",
            7: "готов к диалогу",
            8: "легко идёт на контакт",
            9: "очень сговорчивый",
            10: "соглашается почти на всё"
        }
        
        return f"""Ты играешь роль потенциального клиента автосалона по импорту автомобилей.
Это ТРЕНИРОВОЧНАЯ СИМУЛЯЦИЯ для обучения менеджеров по продажам.

ТВОЙ ПЕРСОНАЖ:
- Манера общения: {rudeness_desc.get(persona.rudeness, "нейтральная")}
- Характер в переговорах: {coop_desc.get(persona.cooperativeness, "нейтральный")}
- Знание рынка: {"эксперт, знает все цены и нюансы" if persona.knowledge_level > 7 else "средний уровень" if persona.knowledge_level > 4 else "новичок, мало понимает"}
- Срочность: {"очень срочно нужна машина" if persona.urgency > 7 else "не особо торопится" if persona.urgency < 4 else "средняя срочность"}
- Доверие: {"очень подозрительный" if persona.trust_level < 4 else "доверяет" if persona.trust_level > 7 else "нейтральное"}

ЧТО ХОЧЕШЬ КУПИТЬ:
- Автомобиль: {persona.desired_car}
- Бюджет: {persona.budget_range}
- Предпочтения по стране: {persona.country_preference}
- Сроки: {persona.timeline}

ТВОИ СКРЫТЫЕ ВОЗРАЖЕНИЯ (не говори о них напрямую, но они влияют на твоё поведение):
{chr(10).join(f"- {obj}" for obj in persona.hidden_objections)}

ЧТО МОЖЕТ ТЕБЯ УБЕДИТЬ КУПИТЬ:
{chr(10).join(f"- {trigger}" for trigger in persona.buying_triggers)}

ПРАВИЛА ПОВЕДЕНИЯ:
1. Веди себя как реальный клиент с этим характером
2. Не раскрывай свои скрытые возражения сразу — пусть менеджер их выявит
3. Если менеджер хорошо работает с возражениями — постепенно становись более открытым
4. Если менеджер давит или хамит — закрывайся или уходи
5. Отвечай коротко (1-3 предложения), как в реальном чате
6. Можешь задавать вопросы, сомневаться, торговаться
7. Если грубость высокая — можешь использовать сленг, быть резким
8. Если сговорчивость низкая — много возражай и сомневайся

ВАЖНО: Ты НЕ продавец, ты КЛИЕНТ. Менеджер должен тебя убедить."""

    @with_retry(max_retries=3, base_delay=1.0)
    async def _call_llm(self, messages: list) -> str:
        """Вызов LLM с retry логикой"""
        response = await self.llm.ainvoke(messages)
        return response.content

    async def process_message(
        self,
        message: str,  # Сообщение от менеджера
        persona: ClientPersona,
        history: list[dict],
        session_id: str | None = None,
    ) -> dict:
        """Обработка сообщения менеджера и генерация ответа клиента"""
        
        if not session_id:
            session_id = str(uuid.uuid4())[:8]
        
        logger.info(f"Simulator processing message for session {session_id}")
        
        # Валидация
        if not message or not message.strip():
            return {
                "response": "...",
                "session_id": session_id,
            }
        
        # Ограничение длины
        if len(message) > 1000:
            message = message[:1000] + "..."
        
        # Проверяем fallback
        if self.error_context.should_use_fallback():
            logger.warning("Simulator using fallback due to consecutive errors")
            return {
                "response": get_fallback_response("simulator"),
                "session_id": session_id,
            }
        
        system_prompt = self._build_system_prompt(persona)
        
        messages = [SystemMessage(content=system_prompt)]
        
        # Добавляем историю (менеджер = user для LLM, клиент = assistant)
        for msg in history:
            if msg["role"] == "manager":
                messages.append(HumanMessage(content=msg["content"]))
            else:
                messages.append(AIMessage(content=msg["content"]))
        
        # Добавляем текущее сообщение менеджера
        messages.append(HumanMessage(content=message))
        
        try:
            # Генерируем ответ клиента
            response_content = await self._call_llm(messages)
            self.error_context.record_success()
            
            return {
                "response": response_content,
                "session_id": session_id,
            }
            
        except AIServiceError as e:
            self.error_context.record_error()
            logger.error(f"Simulator error: {e.message}")
            return {
                "response": e.user_message,
                "session_id": session_id,
                "error": e.user_message,
            }
        except Exception as e:
            self.error_context.record_error()
            logger.error(f"Unexpected simulator error: {e}")
            return {
                "response": get_fallback_response("simulator"),
                "session_id": session_id,
                "error": str(e),
            }
    
    async def evaluate_session(
        self,
        persona: ClientPersona,
        history: list[dict],
    ) -> dict:
        """Оценка работы менеджера по итогам сессии"""
        
        logger.info("Evaluating session")
        
        # Валидация
        if not history or len(history) < 2:
            return self._get_default_evaluation("Недостаточно данных для оценки")
        
        evaluation_prompt = f"""Ты — эксперт по оценке навыков продаж. 
Проанализируй диалог между менеджером по продажам и клиентом.

ПРОФИЛЬ КЛИЕНТА:
- Сговорчивость: {persona.cooperativeness}/10
- Грубость: {persona.rudeness}/10
- Знание рынка: {persona.knowledge_level}/10
- Скрытые возражения: {', '.join(persona.hidden_objections)}
- Триггеры покупки: {', '.join(persona.buying_triggers)}

ДИАЛОГ:
{chr(10).join(f"{'Менеджер' if msg['role'] == 'manager' else 'Клиент'}: {msg['content']}" for msg in history)}

ОЦЕНИ РАБОТУ МЕНЕДЖЕРА ПО КРИТЕРИЯМ (каждый от 0 до 100):

1. **Установление контакта** — насколько хорошо менеджер расположил клиента
2. **Выявление потребностей** — задавал ли правильные вопросы
3. **Работа с возражениями** — как справился со скрытыми возражениями клиента
4. **Презентация** — насколько убедительно представил услуги
5. **Закрытие сделки** — довёл ли до результата

Также укажи:
- Что менеджер сделал хорошо (2-3 пункта)
- Что нужно улучшить (2-3 пункта)
- Общая оценка (0-100)
- Рекомендации для развития

Ответь в формате JSON:
{{
  "scores": {{
    "contact": 0-100,
    "needs_discovery": 0-100,
    "objection_handling": 0-100,
    "presentation": 0-100,
    "closing": 0-100
  }},
  "strengths": ["...", "..."],
  "improvements": ["...", "..."],
  "overall_score": 0-100,
  "recommendations": "..."
}}"""

        try:
            response_content = await self._call_llm([
                SystemMessage(content="Ты эксперт по продажам. Отвечай только валидным JSON."),
                HumanMessage(content=evaluation_prompt)
            ])
            
            # Парсим JSON из ответа
            json_str = response_content.strip()
            json_str = re.sub(r'^```json\s*', '', json_str)
            json_str = re.sub(r'\s*```$', '', json_str)
            
            evaluation = json.loads(json_str)
            
            # Валидация структуры
            if not self._validate_evaluation(evaluation):
                logger.warning("Invalid evaluation structure, using default")
                return self._get_default_evaluation("Ошибка анализа")
            
            return evaluation
            
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing error in evaluation: {e}")
            return self._get_default_evaluation("Ошибка парсинга оценки")
        except AIServiceError as e:
            logger.error(f"AI error in evaluation: {e.message}")
            return self._get_default_evaluation(e.user_message)
        except Exception as e:
            logger.error(f"Unexpected evaluation error: {e}")
            return self._get_default_evaluation("Непредвиденная ошибка")
    
    def _validate_evaluation(self, evaluation: dict) -> bool:
        """Валидация структуры оценки"""
        required_keys = ["scores", "strengths", "improvements", "overall_score", "recommendations"]
        if not all(key in evaluation for key in required_keys):
            return False
        
        score_keys = ["contact", "needs_discovery", "objection_handling", "presentation", "closing"]
        if not all(key in evaluation.get("scores", {}) for key in score_keys):
            return False
        
        return True
    
    def _get_default_evaluation(self, reason: str = "") -> dict:
        """Получить дефолтную оценку при ошибке"""
        return {
            "scores": {
                "contact": 50,
                "needs_discovery": 50,
                "objection_handling": 50,
                "presentation": 50,
                "closing": 50
            },
            "strengths": ["Диалог состоялся"],
            "improvements": [reason or "Требуется больше данных для оценки"],
            "overall_score": 50,
            "recommendations": "Продолжайте практиковаться. Попробуйте провести более длинный диалог."
        }


# Инстанс симулятора
simulator = ClientSimulator()
