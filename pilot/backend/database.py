"""
База данных для хранения лидов, диалогов и каталога автомобилей
"""
from datetime import datetime
from contextlib import asynccontextmanager
import os
from sqlalchemy import Column, Integer, String, DateTime, Text, Float, Boolean, create_engine
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./autoimport.db")

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

Base = declarative_base()


class Lead(Base):
    """Модель лида (потенциального клиента)"""
    __tablename__ = "leads"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(50), unique=True, index=True)
    
    # Контактные данные
    name = Column(String(100), nullable=True)
    phone = Column(String(20), nullable=True)
    email = Column(String(100), nullable=True)
    
    # Параметры запроса
    car_brand = Column(String(50), nullable=True)
    car_model = Column(String(50), nullable=True)
    budget_min = Column(Integer, nullable=True)
    budget_max = Column(Integer, nullable=True)
    country = Column(String(50), nullable=True)  # Страна-источник авто
    timeline = Column(String(50), nullable=True)  # Сроки покупки
    body_type = Column(String(30), nullable=True)  # Тип кузова
    year_min = Column(Integer, nullable=True)
    year_max = Column(Integer, nullable=True)
    
    # Статус и квалификация
    status = Column(String(20), default="new")  # new, in_progress, qualified, converted
    qualification = Column(String(20), nullable=True)  # hot, warm, cold
    
    # Метаданные
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    notes = Column(Text, nullable=True)


class Conversation(Base):
    """Модель сообщения в диалоге"""
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(50), index=True)
    role = Column(String(20))  # user, assistant
    content = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)


class Car(Base):
    """Модель автомобиля в каталоге (готов к перегону)"""
    __tablename__ = "cars"

    id = Column(Integer, primary_key=True, index=True)
    
    # Основные характеристики
    brand = Column(String(50), index=True)  # Toyota, BMW, Mercedes и т.д.
    model = Column(String(100), index=True)  # Camry, X5, E-Class
    year = Column(Integer, index=True)  # Год выпуска
    
    # Цена и локация
    price_usd = Column(Integer, index=True)  # Цена в USD
    price_rub = Column(Integer, index=True)  # Цена в RUB (с учётом доставки и растаможки)
    country = Column(String(50), index=True)  # Страна нахождения: Корея, Япония, Германия, ОАЭ
    city = Column(String(100))  # Город
    
    # Технические характеристики
    mileage_km = Column(Integer)  # Пробег в км
    engine_volume = Column(Float)  # Объём двигателя (л)
    engine_type = Column(String(30))  # Бензин, Дизель, Гибрид, Электро
    transmission = Column(String(30))  # Автомат, Механика, Робот, Вариатор
    drive = Column(String(30))  # Передний, Задний, Полный
    body_type = Column(String(30), index=True)  # Седан, Кроссовер, Внедорожник, Хэтчбек
    color = Column(String(30))  # Цвет
    
    # Комплектация и состояние
    trim = Column(String(100))  # Комплектация
    condition = Column(String(30))  # Отличное, Хорошее, Среднее
    
    # Доставка
    delivery_days = Column(Integer)  # Срок доставки в днях
    in_stock = Column(Boolean, default=True)  # В наличии
    
    # Дополнительно
    vin = Column(String(20), unique=True)  # VIN номер
    description = Column(Text)  # Описание
    photos_url = Column(String(500))  # URL фото (через запятую)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


async def init_db():
    """Инициализация базы данных"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@asynccontextmanager
async def get_db():
    """Контекстный менеджер для сессии БД"""
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
