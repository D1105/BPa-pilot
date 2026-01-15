"""
Скрипт для заполнения базы данных демо-автомобилями
"""
import asyncio
import random
from database import engine, async_session, Base, Car

# Данные для генерации
CARS_DATA = {
    "Toyota": {
        "models": ["Camry", "RAV4", "Land Cruiser 300", "Highlander", "Crown", "Alphard"],
        "country": "Япония",
        "city": "Токио"
    },
    "Hyundai": {
        "models": ["Sonata", "Tucson", "Santa Fe", "Palisade", "Genesis G80", "Grandeur"],
        "country": "Корея",
        "city": "Сеул"
    },
    "Kia": {
        "models": ["K5", "Sportage", "Sorento", "Carnival", "Stinger", "EV6"],
        "country": "Корея",
        "city": "Пусан"
    },
    "BMW": {
        "models": ["3 Series", "5 Series", "X3", "X5", "X7", "7 Series"],
        "country": "Германия",
        "city": "Мюнхен"
    },
    "Mercedes-Benz": {
        "models": ["C-Class", "E-Class", "S-Class", "GLC", "GLE", "GLS"],
        "country": "Германия",
        "city": "Штутгарт"
    },
    "Lexus": {
        "models": ["ES", "RX", "LX", "NX", "GX", "LS"],
        "country": "Япония",
        "city": "Нагоя"
    },
    "Porsche": {
        "models": ["Cayenne", "Macan", "Panamera", "911", "Taycan"],
        "country": "Германия",
        "city": "Штутгарт"
    },
    "Land Rover": {
        "models": ["Range Rover", "Range Rover Sport", "Defender", "Discovery"],
        "country": "ОАЭ",
        "city": "Дубай"
    },
    "Audi": {
        "models": ["A4", "A6", "A8", "Q5", "Q7", "Q8", "e-tron"],
        "country": "Германия",
        "city": "Ингольштадт"
    },
    "Genesis": {
        "models": ["G70", "G80", "G90", "GV70", "GV80"],
        "country": "Корея",
        "city": "Сеул"
    }
}

BODY_TYPES = {
    "Camry": "Седан", "RAV4": "Кроссовер", "Land Cruiser 300": "Внедорожник",
    "Highlander": "Кроссовер", "Crown": "Седан", "Alphard": "Минивэн",
    "Sonata": "Седан", "Tucson": "Кроссовер", "Santa Fe": "Кроссовер",
    "Palisade": "Внедорожник", "Genesis G80": "Седан", "Grandeur": "Седан",
    "K5": "Седан", "Sportage": "Кроссовер", "Sorento": "Кроссовер",
    "Carnival": "Минивэн", "Stinger": "Седан", "EV6": "Кроссовер",
    "3 Series": "Седан", "5 Series": "Седан", "X3": "Кроссовер",
    "X5": "Кроссовер", "X7": "Внедорожник", "7 Series": "Седан",
    "C-Class": "Седан", "E-Class": "Седан", "S-Class": "Седан",
    "GLC": "Кроссовер", "GLE": "Кроссовер", "GLS": "Внедорожник",
    "ES": "Седан", "RX": "Кроссовер", "LX": "Внедорожник",
    "NX": "Кроссовер", "GX": "Внедорожник", "LS": "Седан",
    "Cayenne": "Кроссовер", "Macan": "Кроссовер", "Panamera": "Седан",
    "911": "Купе", "Taycan": "Седан",
    "Range Rover": "Внедорожник", "Range Rover Sport": "Внедорожник",
    "Defender": "Внедорожник", "Discovery": "Внедорожник",
    "A4": "Седан", "A6": "Седан", "A8": "Седан",
    "Q5": "Кроссовер", "Q7": "Внедорожник", "Q8": "Кроссовер", "e-tron": "Кроссовер",
    "G70": "Седан", "G80": "Седан", "G90": "Седан",
    "GV70": "Кроссовер", "GV80": "Кроссовер"
}

ENGINE_TYPES = ["Бензин", "Дизель", "Гибрид"]
TRANSMISSIONS = ["Автомат", "Робот"]
DRIVES = ["Передний", "Задний", "Полный"]
COLORS = ["Белый", "Чёрный", "Серебристый", "Серый", "Синий", "Красный", "Коричневый"]
CONDITIONS = ["Отличное", "Хорошее", "Хорошее", "Отличное"]  # Weighted towards good

# Ценовые диапазоны по маркам (в USD)
PRICE_RANGES = {
    "Toyota": (25000, 80000),
    "Hyundai": (20000, 55000),
    "Kia": (18000, 50000),
    "BMW": (35000, 120000),
    "Mercedes-Benz": (40000, 150000),
    "Lexus": (35000, 100000),
    "Porsche": (60000, 200000),
    "Land Rover": (50000, 180000),
    "Audi": (30000, 100000),
    "Genesis": (35000, 90000)
}

# Сроки доставки по странам (дни)
DELIVERY_DAYS = {
    "Япония": (25, 40),
    "Корея": (20, 35),
    "Германия": (30, 50),
    "ОАЭ": (15, 25)
}


def generate_vin():
    """Генерация случайного VIN"""
    chars = "ABCDEFGHJKLMNPRSTUVWXYZ0123456789"
    return ''.join(random.choices(chars, k=17))


def generate_car(brand: str, model: str, idx: int) -> dict:
    """Генерация данных одного автомобиля"""
    data = CARS_DATA[brand]
    price_min, price_max = PRICE_RANGES[brand]
    delivery_min, delivery_max = DELIVERY_DAYS[data["country"]]
    
    year = random.randint(2020, 2024)
    price_usd = random.randint(price_min, price_max)
    # Курс ~90 руб/USD + наценка 15-25% за доставку и растаможку
    markup = random.uniform(1.15, 1.25)
    price_rub = int(price_usd * 90 * markup)
    
    mileage = random.randint(0, 80000) if year < 2024 else random.randint(0, 15000)
    
    engine_volume = random.choice([1.6, 2.0, 2.4, 2.5, 3.0, 3.5, 4.0])
    
    # Электро для определённых моделей
    if model in ["EV6", "e-tron", "Taycan"]:
        engine_type = "Электро"
        engine_volume = 0.0
    else:
        engine_type = random.choice(ENGINE_TYPES)
    
    return {
        "brand": brand,
        "model": model,
        "year": year,
        "price_usd": price_usd,
        "price_rub": price_rub,
        "country": data["country"],
        "city": data["city"],
        "mileage_km": mileage,
        "engine_volume": engine_volume,
        "engine_type": engine_type,
        "transmission": random.choice(TRANSMISSIONS),
        "drive": random.choice(DRIVES),
        "body_type": BODY_TYPES.get(model, "Седан"),
        "color": random.choice(COLORS),
        "trim": random.choice(["Base", "Comfort", "Premium", "Luxury", "Sport"]),
        "condition": random.choice(CONDITIONS),
        "delivery_days": random.randint(delivery_min, delivery_max),
        "in_stock": True,
        "vin": generate_vin(),
        "description": f"{brand} {model} {year} года в отличном состоянии. Полный пакет документов, готов к отправке.",
        "photos_url": f"https://example.com/cars/{brand.lower()}/{model.lower()}/{idx}.jpg"
    }


async def seed_database():
    """Заполнение базы данных автомобилями"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async with async_session() as session:
        # Проверяем, есть ли уже данные
        from sqlalchemy import select, func
        result = await session.execute(select(func.count(Car.id)))
        count = result.scalar()
        
        if count > 0:
            print(f"База уже содержит {count} автомобилей. Очищаем...")
            await session.execute(Car.__table__.delete())
            await session.commit()
        
        cars = []
        idx = 0
        
        # Генерируем по 5-8 авто каждой модели
        for brand, data in CARS_DATA.items():
            for model in data["models"]:
                num_cars = random.randint(3, 6)
                for _ in range(num_cars):
                    car_data = generate_car(brand, model, idx)
                    cars.append(Car(**car_data))
                    idx += 1
        
        session.add_all(cars)
        await session.commit()
        
        print(f"[OK] Dobavleno {len(cars)} avtomobilej v katalog")
        
        # Статистика
        print("\nStatistika po markam:")
        for brand in CARS_DATA.keys():
            result = await session.execute(
                select(func.count(Car.id)).where(Car.brand == brand)
            )
            brand_count = result.scalar()
            print(f"  {brand}: {brand_count} avto")
        
        print("\nStatistika po stranam:")
        for country in ["Япония", "Корея", "Германия", "ОАЭ"]:
            result = await session.execute(
                select(func.count(Car.id)).where(Car.country == country)
            )
            country_count = result.scalar()
            print(f"  {country}: {country_count} avto")


if __name__ == "__main__":
    asyncio.run(seed_database())
