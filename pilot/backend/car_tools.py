"""
Tools для поиска автомобилей в каталоге
"""
from typing import Optional, List, Dict, Any
from sqlalchemy import select, and_, or_
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_core.tools import tool
from pydantic import BaseModel, Field

from database import Car, async_session


class CarSearchParams(BaseModel):
    """Параметры поиска автомобилей"""
    brand: Optional[str] = Field(None, description="Марка автомобиля (Toyota, BMW, Mercedes-Benz и т.д.)")
    model: Optional[str] = Field(None, description="Модель автомобиля (Camry, X5, E-Class и т.д.)")
    price_min: Optional[int] = Field(None, description="Минимальная цена в рублях")
    price_max: Optional[int] = Field(None, description="Максимальная цена в рублях")
    year_min: Optional[int] = Field(None, description="Минимальный год выпуска")
    year_max: Optional[int] = Field(None, description="Максимальный год выпуска")
    country: Optional[str] = Field(None, description="Страна нахождения (Япония, Корея, Германия, ОАЭ)")
    body_type: Optional[str] = Field(None, description="Тип кузова (Седан, Кроссовер, Внедорожник)")
    engine_type: Optional[str] = Field(None, description="Тип двигателя (Бензин, Дизель, Гибрид, Электро)")
    mileage_max: Optional[int] = Field(None, description="Максимальный пробег в км")
    limit: int = Field(5, description="Максимальное количество результатов (по умолчанию 5)")


async def search_cars_in_db(params: CarSearchParams) -> List[Dict[str, Any]]:
    """
    Поиск автомобилей в базе данных с фильтрами.
    Возвращает список автомобилей, соответствующих критериям.
    """
    async with async_session() as session:
        query = select(Car).where(Car.in_stock == True)
        
        conditions = []
        
        # Фильтр по марке (нечёткий поиск)
        if params.brand:
            brand_lower = params.brand.lower()
            # Маппинг альтернативных названий
            brand_mapping = {
                "мерседес": "Mercedes-Benz",
                "mercedes": "Mercedes-Benz",
                "мерс": "Mercedes-Benz",
                "бмв": "BMW",
                "bmw": "BMW",
                "тойота": "Toyota",
                "toyota": "Toyota",
                "лексус": "Lexus",
                "lexus": "Lexus",
                "хендай": "Hyundai",
                "хундай": "Hyundai",
                "hyundai": "Hyundai",
                "хёндай": "Hyundai",
                "киа": "Kia",
                "kia": "Kia",
                "ауди": "Audi",
                "audi": "Audi",
                "порше": "Porsche",
                "porsche": "Porsche",
                "ленд ровер": "Land Rover",
                "land rover": "Land Rover",
                "рендж ровер": "Land Rover",
                "range rover": "Land Rover",
                "генезис": "Genesis",
                "genesis": "Genesis",
            }
            normalized_brand = brand_mapping.get(brand_lower, params.brand)
            conditions.append(Car.brand.ilike(f"%{normalized_brand}%"))
        
        # Фильтр по модели
        if params.model:
            conditions.append(Car.model.ilike(f"%{params.model}%"))
        
        # Фильтр по цене (в рублях)
        if params.price_min:
            conditions.append(Car.price_rub >= params.price_min)
        if params.price_max:
            conditions.append(Car.price_rub <= params.price_max)
        
        # Фильтр по году
        if params.year_min:
            conditions.append(Car.year >= params.year_min)
        if params.year_max:
            conditions.append(Car.year <= params.year_max)
        
        # Фильтр по стране
        if params.country:
            country_lower = params.country.lower()
            country_mapping = {
                "япония": "Япония",
                "japan": "Япония",
                "корея": "Корея",
                "korea": "Корея",
                "южная корея": "Корея",
                "германия": "Германия",
                "germany": "Германия",
                "оаэ": "ОАЭ",
                "эмираты": "ОАЭ",
                "дубай": "ОАЭ",
                "uae": "ОАЭ",
            }
            normalized_country = country_mapping.get(country_lower, params.country)
            conditions.append(Car.country == normalized_country)
        
        # Фильтр по типу кузова
        if params.body_type:
            body_mapping = {
                "седан": "Седан",
                "кроссовер": "Кроссовер",
                "внедорожник": "Внедорожник",
                "хэтчбек": "Хэтчбек",
                "минивэн": "Минивэн",
                "купе": "Купе",
            }
            normalized_body = body_mapping.get(params.body_type.lower(), params.body_type)
            conditions.append(Car.body_type == normalized_body)
        
        # Фильтр по типу двигателя
        if params.engine_type:
            engine_mapping = {
                "бензин": "Бензин",
                "дизель": "Дизель",
                "гибрид": "Гибрид",
                "электро": "Электро",
                "электрический": "Электро",
            }
            normalized_engine = engine_mapping.get(params.engine_type.lower(), params.engine_type)
            conditions.append(Car.engine_type == normalized_engine)
        
        # Фильтр по пробегу
        if params.mileage_max:
            conditions.append(Car.mileage_km <= params.mileage_max)
        
        # Применяем все условия
        if conditions:
            query = query.where(and_(*conditions))
        
        # Сортировка по цене и лимит
        query = query.order_by(Car.price_rub).limit(params.limit)
        
        result = await session.execute(query)
        cars = result.scalars().all()
        
        # Форматируем результат
        return [
            {
                "id": car.id,
                "brand": car.brand,
                "model": car.model,
                "year": car.year,
                "price_usd": car.price_usd,
                "price_rub": car.price_rub,
                "price_formatted": f"{car.price_rub:,}".replace(",", " ") + " руб.",
                "country": car.country,
                "city": car.city,
                "mileage_km": car.mileage_km,
                "mileage_formatted": f"{car.mileage_km:,}".replace(",", " ") + " км",
                "engine_volume": car.engine_volume,
                "engine_type": car.engine_type,
                "transmission": car.transmission,
                "drive": car.drive,
                "body_type": car.body_type,
                "color": car.color,
                "trim": car.trim,
                "condition": car.condition,
                "delivery_days": car.delivery_days,
                "vin": car.vin,
                "description": car.description,
            }
            for car in cars
        ]


def format_car_for_chat(car: Dict[str, Any]) -> str:
    """Форматирование информации об автомобиле для чата"""
    return (
        f"**{car['brand']} {car['model']} {car['year']}**\n"
        f"- Цена: {car['price_formatted']}\n"
        f"- Пробег: {car['mileage_formatted']}\n"
        f"- Двигатель: {car['engine_volume']}л {car['engine_type']}\n"
        f"- КПП: {car['transmission']}, привод: {car['drive']}\n"
        f"- Кузов: {car['body_type']}, цвет: {car['color']}\n"
        f"- Страна: {car['country']} ({car['city']})\n"
        f"- Доставка: ~{car['delivery_days']} дней\n"
        f"- Состояние: {car['condition']}"
    )


def format_cars_list_for_chat(cars: List[Dict[str, Any]]) -> str:
    """Форматирование списка автомобилей для чата"""
    if not cars:
        return "К сожалению, по вашим критериям автомобилей не найдено. Попробуйте изменить параметры поиска."
    
    result = f"Найдено {len(cars)} автомобилей:\n\n"
    for i, car in enumerate(cars, 1):
        result += f"{i}. {format_car_for_chat(car)}\n\n"
    
    return result


# Создаём tool для LangChain
@tool
async def search_cars(
    brand: Optional[str] = None,
    model: Optional[str] = None,
    price_min: Optional[int] = None,
    price_max: Optional[int] = None,
    year_min: Optional[int] = None,
    year_max: Optional[int] = None,
    country: Optional[str] = None,
    body_type: Optional[str] = None,
    engine_type: Optional[str] = None,
    mileage_max: Optional[int] = None,
    limit: int = 5
) -> str:
    """
    Поиск автомобилей в каталоге по заданным критериям.
    Используй этот инструмент когда клиент спрашивает о наличии конкретных автомобилей,
    хочет узнать цены или посмотреть варианты.
    
    Args:
        brand: Марка автомобиля (Toyota, BMW, Mercedes-Benz, Hyundai, Kia, Lexus, Audi, Porsche, Land Rover, Genesis)
        model: Модель автомобиля
        price_min: Минимальная цена в рублях
        price_max: Максимальная цена в рублях
        year_min: Минимальный год выпуска
        year_max: Максимальный год выпуска
        country: Страна нахождения (Япония, Корея, Германия, ОАЭ)
        body_type: Тип кузова (Седан, Кроссовер, Внедорожник, Хэтчбек, Минивэн, Купе)
        engine_type: Тип двигателя (Бензин, Дизель, Гибрид, Электро)
        mileage_max: Максимальный пробег в км
        limit: Количество результатов (по умолчанию 5)
    
    Returns:
        Форматированный список найденных автомобилей
    """
    params = CarSearchParams(
        brand=brand,
        model=model,
        price_min=price_min,
        price_max=price_max,
        year_min=year_min,
        year_max=year_max,
        country=country,
        body_type=body_type,
        engine_type=engine_type,
        mileage_max=mileage_max,
        limit=limit
    )
    
    cars = await search_cars_in_db(params)
    return format_cars_list_for_chat(cars)


@tool
async def get_available_brands() -> str:
    """
    Получить список доступных марок автомобилей в каталоге.
    Используй когда клиент спрашивает какие марки есть в наличии.
    
    Returns:
        Список марок с количеством автомобилей
    """
    async with async_session() as session:
        from sqlalchemy import func
        
        query = (
            select(Car.brand, func.count(Car.id).label('count'))
            .where(Car.in_stock == True)
            .group_by(Car.brand)
            .order_by(func.count(Car.id).desc())
        )
        
        result = await session.execute(query)
        brands = result.all()
        
        if not brands:
            return "В данный момент каталог пуст."
        
        lines = ["В наличии автомобили следующих марок:"]
        for brand, count in brands:
            lines.append(f"- {brand}: {count} авто")
        
        return "\n".join(lines)


@tool
async def get_price_range(brand: Optional[str] = None, model: Optional[str] = None) -> str:
    """
    Получить диапазон цен на автомобили.
    Используй когда клиент спрашивает о ценах на конкретную марку или модель.
    
    Args:
        brand: Марка автомобиля (опционально)
        model: Модель автомобиля (опционально)
    
    Returns:
        Информация о диапазоне цен
    """
    async with async_session() as session:
        from sqlalchemy import func
        
        query = select(
            func.min(Car.price_rub).label('min_price'),
            func.max(Car.price_rub).label('max_price'),
            func.avg(Car.price_rub).label('avg_price'),
            func.count(Car.id).label('count')
        ).where(Car.in_stock == True)
        
        if brand:
            query = query.where(Car.brand.ilike(f"%{brand}%"))
        if model:
            query = query.where(Car.model.ilike(f"%{model}%"))
        
        result = await session.execute(query)
        row = result.one()
        
        if row.count == 0:
            return "По указанным критериям автомобилей не найдено."
        
        min_price = f"{int(row.min_price):,}".replace(",", " ")
        max_price = f"{int(row.max_price):,}".replace(",", " ")
        avg_price = f"{int(row.avg_price):,}".replace(",", " ")
        
        brand_text = f" {brand}" if brand else ""
        model_text = f" {model}" if model else ""
        
        return (
            f"Цены на{brand_text}{model_text} ({row.count} авто в наличии):\n"
            f"- Минимальная: {min_price} руб.\n"
            f"- Максимальная: {max_price} руб.\n"
            f"- Средняя: {avg_price} руб."
        )


# Список всех tools для экспорта
CAR_TOOLS = [search_cars, get_available_brands, get_price_range]
