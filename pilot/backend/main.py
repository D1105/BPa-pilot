"""
АвтоИмпорт Pro - Пилотный ИИ-агент для продаж автомобилей
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field, validator
from pathlib import Path
from dotenv import load_dotenv
import time

# Загружаем .env (сначала из pilot/backend/.env, потом из корня для обратной совместимости)
env_path_local = Path(__file__).parent / ".env"
env_path_root = Path(__file__).parent.parent.parent / ".env"
if env_path_local.exists():
    load_dotenv(env_path_local)
elif env_path_root.exists():
    load_dotenv(env_path_root)
else:
    # Используем переменные окружения системы
    load_dotenv()

from agent import AutoImportAgent
from database import init_db, get_db, Lead, Conversation
from simulator import ClientSimulator, ClientPersona
from errors import logger, AIServiceError, get_fallback_response

agent = AutoImportAgent()
simulator = ClientSimulator()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting АвтоИмпорт Pro API...")
    await init_db()
    logger.info("Database initialized")
    yield
    logger.info("Shutting down...")


app = FastAPI(
    title="АвтоИмпорт Pro API",
    description="ИИ-агент для автоматизации продаж автомобилей",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============== MIDDLEWARE ==============

@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Логирование запросов и времени выполнения"""
    start_time = time.time()
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    logger.info(
        f"{request.method} {request.url.path} - "
        f"Status: {response.status_code} - "
        f"Time: {process_time:.3f}s"
    )
    
    return response


# ============== EXCEPTION HANDLERS ==============

@app.exception_handler(AIServiceError)
async def ai_service_error_handler(request: Request, exc: AIServiceError):
    """Обработка ошибок AI-сервиса"""
    logger.error(f"AI Service Error: {exc.message}")
    return JSONResponse(
        status_code=503 if exc.recoverable else 500,
        content={
            "error": exc.user_message,
            "recoverable": exc.recoverable,
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Общий обработчик исключений"""
    logger.error(f"Unhandled exception: {type(exc).__name__}: {exc}")
    return JSONResponse(
        status_code=500,
        content={
            "error": "Произошла внутренняя ошибка сервера. Попробуйте позже.",
            "recoverable": True,
        }
    )


# ============== MODELS ==============

class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=2000)
    history: list[ChatMessage] = []
    session_id: str | None = None
    
    @validator('message')
    def message_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Сообщение не может быть пустым')
        return v.strip()


class ChatResponse(BaseModel):
    response: str
    session_id: str
    extracted_data: dict | None = None
    lead_status: str | None = None
    error: str | None = None


class LeadResponse(BaseModel):
    id: int
    session_id: str
    name: str | None
    phone: str | None
    car_brand: str | None
    car_model: str | None
    budget_min: int | None
    budget_max: int | None
    country: str | None
    timeline: str | None
    status: str
    qualification: str | None
    created_at: str


class ErrorResponse(BaseModel):
    error: str
    recoverable: bool = True


# ============== HEALTH CHECK ==============

@app.get("/")
async def root():
    return {"status": "ok", "service": "АвтоИмпорт Pro API"}


@app.get("/health")
async def health_check():
    """Проверка здоровья сервиса"""
    try:
        # Проверяем БД
        async with get_db() as db:
            from sqlalchemy import text
            await db.execute(text("SELECT 1"))
        
        return {
            "status": "healthy",
            "database": "connected",
            "openai_configured": bool(os.getenv("OPENAI_API_KEY")),
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "error": str(e),
            }
        )


# ============== CHAT API ==============

@app.post("/api/chat", response_model=ChatResponse, responses={503: {"model": ErrorResponse}})
async def chat(request: ChatRequest):
    """Основной эндпоинт чата с ИИ-агентом"""
    try:
        result = await agent.process_message(
            message=request.message,
            history=[{"role": m.role, "content": m.content} for m in request.history],
            session_id=request.session_id,
        )
        return ChatResponse(
            response=result["response"],
            session_id=result["session_id"],
            extracted_data=result.get("extracted_data"),
            lead_status=result.get("lead_status"),
            error=result.get("error"),
        )
    except AIServiceError as e:
        # Возвращаем fallback ответ вместо ошибки
        return ChatResponse(
            response=e.user_message,
            session_id=request.session_id or "error",
            error=e.user_message,
        )
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return ChatResponse(
            response=get_fallback_response("general"),
            session_id=request.session_id or "error",
            error="Внутренняя ошибка сервера",
        )


# ============== LEADS API ==============

@app.get("/api/leads", response_model=list[LeadResponse])
async def get_leads():
    """Получить список всех лидов"""
    try:
        async with get_db() as db:
            from sqlalchemy import select
            result = await db.execute(select(Lead).order_by(Lead.created_at.desc()))
            leads = result.scalars().all()
            return [
                LeadResponse(
                    id=lead.id,
                    session_id=lead.session_id,
                    name=lead.name,
                    phone=lead.phone,
                    car_brand=lead.car_brand,
                    car_model=lead.car_model,
                    budget_min=lead.budget_min,
                    budget_max=lead.budget_max,
                    country=lead.country,
                    timeline=lead.timeline,
                    status=lead.status,
                    qualification=lead.qualification,
                    created_at=lead.created_at.isoformat(),
                )
                for lead in leads
            ]
    except Exception as e:
        logger.error(f"Error fetching leads: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения лидов")


@app.get("/api/leads/{session_id}")
async def get_lead(session_id: str):
    """Получить лид по session_id"""
    try:
        async with get_db() as db:
            from sqlalchemy import select
            result = await db.execute(
                select(Lead).where(Lead.session_id == session_id)
            )
            lead = result.scalar_one_or_none()
            if not lead:
                raise HTTPException(status_code=404, detail="Лид не найден")
            return lead
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching lead {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения лида")


@app.get("/api/conversations/{session_id}")
async def get_conversation(session_id: str):
    """Получить историю диалога"""
    try:
        async with get_db() as db:
            from sqlalchemy import select
            result = await db.execute(
                select(Conversation)
                .where(Conversation.session_id == session_id)
                .order_by(Conversation.created_at)
            )
            messages = result.scalars().all()
            return [
                {
                    "role": msg.role,
                    "content": msg.content,
                    "created_at": msg.created_at.isoformat(),
                }
                for msg in messages
            ]
    except Exception as e:
        logger.error(f"Error fetching conversation {session_id}: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения диалога")


@app.get("/api/stats")
async def get_stats():
    """Статистика по лидам"""
    try:
        async with get_db() as db:
            from sqlalchemy import select, func
            
            total = await db.execute(select(func.count(Lead.id)))
            total_count = total.scalar() or 0
            
            qualified = await db.execute(
                select(func.count(Lead.id)).where(Lead.qualification == "hot")
            )
            hot_count = qualified.scalar() or 0
            
            warm = await db.execute(
                select(func.count(Lead.id)).where(Lead.qualification == "warm")
            )
            warm_count = warm.scalar() or 0
            
            return {
                "total_leads": total_count,
                "hot_leads": hot_count,
                "warm_leads": warm_count,
                "cold_leads": max(0, total_count - hot_count - warm_count),
            }
    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения статистики")


# ============== КАТАЛОГ АВТОМОБИЛЕЙ ==============

from car_tools import search_cars_in_db, CarSearchParams
from database import Car

class CarSearchRequest(BaseModel):
    brand: str | None = None
    model: str | None = None
    price_min: int | None = None
    price_max: int | None = None
    year_min: int | None = None
    year_max: int | None = None
    country: str | None = None
    body_type: str | None = None
    engine_type: str | None = None
    mileage_max: int | None = None
    limit: int = 20


@app.get("/api/cars")
async def get_cars(
    brand: str | None = None,
    model: str | None = None,
    price_min: int | None = None,
    price_max: int | None = None,
    year_min: int | None = None,
    year_max: int | None = None,
    country: str | None = None,
    body_type: str | None = None,
    limit: int = 20
):
    """Получить список автомобилей с фильтрацией"""
    try:
        params = CarSearchParams(
            brand=brand,
            model=model,
            price_min=price_min,
            price_max=price_max,
            year_min=year_min,
            year_max=year_max,
            country=country,
            body_type=body_type,
            limit=limit
        )
        cars = await search_cars_in_db(params)
        return {"cars": cars, "count": len(cars)}
    except Exception as e:
        logger.error(f"Error fetching cars: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения каталога")


@app.post("/api/cars/search")
async def search_cars_api(request: CarSearchRequest):
    """Поиск автомобилей с фильтрами (POST)"""
    try:
        params = CarSearchParams(**request.model_dump())
        cars = await search_cars_in_db(params)
        return {"cars": cars, "count": len(cars)}
    except Exception as e:
        logger.error(f"Error searching cars: {e}")
        raise HTTPException(status_code=500, detail="Ошибка поиска автомобилей")


@app.get("/api/cars/stats")
async def get_cars_stats():
    """Статистика по каталогу автомобилей"""
    try:
        async with get_db() as db:
            from sqlalchemy import select, func
            
            # Общее количество
            total = await db.execute(select(func.count(Car.id)).where(Car.in_stock == True))
            total_count = total.scalar() or 0
            
            # По маркам
            brands_query = (
                select(Car.brand, func.count(Car.id).label('count'))
                .where(Car.in_stock == True)
                .group_by(Car.brand)
                .order_by(func.count(Car.id).desc())
            )
            brands_result = await db.execute(brands_query)
            brands = {row[0]: row[1] for row in brands_result.all()}
            
            # По странам
            countries_query = (
                select(Car.country, func.count(Car.id).label('count'))
                .where(Car.in_stock == True)
                .group_by(Car.country)
            )
            countries_result = await db.execute(countries_query)
            countries = {row[0]: row[1] for row in countries_result.all()}
            
            # Ценовой диапазон
            price_query = select(
                func.min(Car.price_rub).label('min'),
                func.max(Car.price_rub).label('max'),
                func.avg(Car.price_rub).label('avg')
            ).where(Car.in_stock == True)
            price_result = await db.execute(price_query)
            price_row = price_result.one()
            
            return {
                "total_cars": total_count,
                "by_brand": brands,
                "by_country": countries,
                "price_range": {
                    "min": int(price_row.min) if price_row.min else 0,
                    "max": int(price_row.max) if price_row.max else 0,
                    "avg": int(price_row.avg) if price_row.avg else 0,
                }
            }
    except Exception as e:
        logger.error(f"Error fetching cars stats: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения статистики каталога")


@app.get("/api/cars/{car_id}")
async def get_car(car_id: int):
    """Получить информацию об автомобиле по ID"""
    try:
        async with get_db() as db:
            from sqlalchemy import select
            result = await db.execute(select(Car).where(Car.id == car_id))
            car = result.scalar_one_or_none()
            if not car:
                raise HTTPException(status_code=404, detail="Автомобиль не найден")
            return {
                "id": car.id,
                "brand": car.brand,
                "model": car.model,
                "year": car.year,
                "price_usd": car.price_usd,
                "price_rub": car.price_rub,
                "country": car.country,
                "city": car.city,
                "mileage_km": car.mileage_km,
                "engine_volume": car.engine_volume,
                "engine_type": car.engine_type,
                "transmission": car.transmission,
                "drive": car.drive,
                "body_type": car.body_type,
                "color": car.color,
                "trim": car.trim,
                "condition": car.condition,
                "delivery_days": car.delivery_days,
                "in_stock": car.in_stock,
                "vin": car.vin,
                "description": car.description,
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching car {car_id}: {e}")
        raise HTTPException(status_code=500, detail="Ошибка получения автомобиля")


# ============== СИМУЛЯТОР КЛИЕНТА ДЛЯ ТРЕНИРОВКИ ==============

class SimulatorMessage(BaseModel):
    role: str  # "manager" или "client"
    content: str


class SimulatorRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=1000)
    history: list[SimulatorMessage] = []
    session_id: str | None = None
    persona: ClientPersona | None = None
    preset: str | None = None  # "easy", "medium", "hard", "nightmare"
    
    @validator('message')
    def message_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Сообщение не может быть пустым')
        return v.strip()
    
    @validator('preset')
    def valid_preset(cls, v):
        if v and v not in ["easy", "medium", "hard", "nightmare"]:
            raise ValueError('Неверный пресет. Доступны: easy, medium, hard, nightmare')
        return v


class SimulatorResponse(BaseModel):
    response: str
    session_id: str
    persona_name: str
    error: str | None = None


class EvaluationRequest(BaseModel):
    history: list[SimulatorMessage] = Field(..., min_items=2)
    persona: ClientPersona | None = None
    preset: str | None = None


@app.get("/api/simulator/presets")
async def get_simulator_presets():
    """Получить список пресетов клиентов"""
    return {
        "presets": [
            {
                "id": "easy",
                "name": "🟢 Лёгкий клиент",
                "description": "Вежливый, готов к покупке, мало возражений",
                "difficulty": 1,
            },
            {
                "id": "medium",
                "name": "🟡 Средний клиент",
                "description": "Сомневается, есть скрытые возражения",
                "difficulty": 2,
            },
            {
                "id": "hard",
                "name": "🔴 Сложный клиент",
                "description": "Скептик, много возражений, требует доказательств",
                "difficulty": 3,
            },
            {
                "id": "nightmare",
                "name": "💀 Кошмарный клиент",
                "description": "Хам, не собирается покупать, провоцирует",
                "difficulty": 4,
            },
        ]
    }


@app.post("/api/simulator/chat", response_model=SimulatorResponse)
async def simulator_chat(request: SimulatorRequest):
    """Чат с симулятором клиента"""
    try:
        # Определяем персону
        if request.preset and request.preset in ClientSimulator.PERSONA_PRESETS:
            persona = ClientSimulator.PERSONA_PRESETS[request.preset]
            persona_name = request.preset
        elif request.persona:
            persona = request.persona
            persona_name = "custom"
        else:
            persona = ClientSimulator.PERSONA_PRESETS["medium"]
            persona_name = "medium"
        
        result = await simulator.process_message(
            message=request.message,
            persona=persona,
            history=[{"role": m.role, "content": m.content} for m in request.history],
            session_id=request.session_id,
        )
        
        return SimulatorResponse(
            response=result["response"],
            session_id=result["session_id"],
            persona_name=persona_name,
            error=result.get("error"),
        )
    except AIServiceError as e:
        return SimulatorResponse(
            response=e.user_message,
            session_id=request.session_id or "error",
            persona_name="error",
            error=e.user_message,
        )
    except Exception as e:
        logger.error(f"Simulator chat error: {e}")
        return SimulatorResponse(
            response=get_fallback_response("simulator"),
            session_id=request.session_id or "error",
            persona_name="error",
            error="Внутренняя ошибка симулятора",
        )


@app.post("/api/simulator/evaluate")
async def simulator_evaluate(request: EvaluationRequest):
    """Оценка работы менеджера по итогам сессии"""
    try:
        # Определяем персону
        if request.preset and request.preset in ClientSimulator.PERSONA_PRESETS:
            persona = ClientSimulator.PERSONA_PRESETS[request.preset]
        elif request.persona:
            persona = request.persona
        else:
            persona = ClientSimulator.PERSONA_PRESETS["medium"]
        
        evaluation = await simulator.evaluate_session(
            persona=persona,
            history=[{"role": m.role, "content": m.content} for m in request.history],
        )
        
        return evaluation
    except Exception as e:
        logger.error(f"Evaluation error: {e}")
        # Возвращаем дефолтную оценку вместо ошибки
        return {
            "scores": {
                "contact": 50,
                "needs_discovery": 50,
                "objection_handling": 50,
                "presentation": 50,
                "closing": 50
            },
            "strengths": ["Диалог состоялся"],
            "improvements": ["Ошибка при анализе. Попробуйте ещё раз."],
            "overall_score": 50,
            "recommendations": "Произошла ошибка при оценке. Попробуйте провести новую сессию."
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
