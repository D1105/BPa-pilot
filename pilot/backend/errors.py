"""
Модуль обработки ошибок и graceful degradation
"""
import logging
from functools import wraps
from typing import Callable, Any
import asyncio

from openai import (
    APIError,
    APIConnectionError,
    RateLimitError,
    APITimeoutError,
    AuthenticationError,
)

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("autoimport")


class AIServiceError(Exception):
    """Базовая ошибка AI-сервиса"""
    def __init__(self, message: str, user_message: str, recoverable: bool = True):
        self.message = message
        self.user_message = user_message  # Сообщение для пользователя
        self.recoverable = recoverable
        super().__init__(message)


class RateLimitExceeded(AIServiceError):
    """Превышен лимит запросов"""
    def __init__(self):
        super().__init__(
            message="OpenAI rate limit exceeded",
            user_message="Сервис временно перегружен. Пожалуйста, подождите несколько секунд и попробуйте снова.",
            recoverable=True
        )


class AIConnectionError(AIServiceError):
    """Ошибка подключения к AI"""
    def __init__(self):
        super().__init__(
            message="Failed to connect to OpenAI API",
            user_message="Не удалось подключиться к сервису. Проверьте интернет-соединение.",
            recoverable=True
        )


class AITimeoutError(AIServiceError):
    """Таймаут запроса к AI"""
    def __init__(self):
        super().__init__(
            message="OpenAI API request timed out",
            user_message="Запрос занял слишком много времени. Попробуйте ещё раз.",
            recoverable=True
        )


class AIAuthError(AIServiceError):
    """Ошибка аутентификации"""
    def __init__(self):
        super().__init__(
            message="OpenAI API authentication failed",
            user_message="Ошибка конфигурации сервиса. Обратитесь к администратору.",
            recoverable=False
        )


class DatabaseError(AIServiceError):
    """Ошибка базы данных"""
    def __init__(self, original_error: str = ""):
        super().__init__(
            message=f"Database error: {original_error}",
            user_message="Временная ошибка сохранения данных. Ваше сообщение обработано.",
            recoverable=True
        )


# Fallback ответы для graceful degradation
FALLBACK_RESPONSES = {
    "greeting": "Здравствуйте! 👋 Я консультант АвтоИмпорт Pro. К сожалению, сейчас у меня технические сложности, но я скоро вернусь. Оставьте ваш вопрос, и мы обязательно свяжемся с вами!",
    "general": "Извините, возникла техническая ошибка. Пожалуйста, попробуйте ещё раз через несколько секунд. Если проблема повторится — оставьте ваш телефон, и менеджер свяжется с вами.",
    "rate_limit": "Сервис временно перегружен из-за большого количества запросов. Пожалуйста, подождите 10-15 секунд и попробуйте снова.",
    "simulator": "Симулятор временно недоступен. Попробуйте позже или выберите другой тип клиента.",
}


def get_fallback_response(context: str = "general") -> str:
    """Получить fallback-ответ для graceful degradation"""
    return FALLBACK_RESPONSES.get(context, FALLBACK_RESPONSES["general"])


def handle_openai_error(error: Exception) -> AIServiceError:
    """Преобразование ошибок OpenAI в наши типы"""
    if isinstance(error, RateLimitError):
        logger.warning(f"Rate limit exceeded: {error}")
        return RateLimitExceeded()
    elif isinstance(error, APIConnectionError):
        logger.error(f"Connection error: {error}")
        return AIConnectionError()
    elif isinstance(error, APITimeoutError):
        logger.warning(f"Timeout error: {error}")
        return AITimeoutError()
    elif isinstance(error, AuthenticationError):
        logger.critical(f"Authentication error: {error}")
        return AIAuthError()
    elif isinstance(error, APIError):
        logger.error(f"API error: {error}")
        return AIServiceError(
            message=str(error),
            user_message="Произошла ошибка при обработке запроса. Попробуйте ещё раз.",
            recoverable=True
        )
    else:
        logger.error(f"Unknown error: {type(error).__name__}: {error}")
        return AIServiceError(
            message=str(error),
            user_message="Произошла непредвиденная ошибка. Мы уже работаем над её устранением.",
            recoverable=True
        )


def with_retry(
    max_retries: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 10.0,
    exponential_backoff: bool = True,
):
    """
    Декоратор для повторных попыток при ошибках
    
    Args:
        max_retries: Максимальное количество попыток
        base_delay: Базовая задержка между попытками (секунды)
        max_delay: Максимальная задержка
        exponential_backoff: Использовать экспоненциальную задержку
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            last_error = None
            
            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except (RateLimitError, APIConnectionError, APITimeoutError) as e:
                    last_error = e
                    
                    if attempt < max_retries - 1:
                        if exponential_backoff:
                            delay = min(base_delay * (2 ** attempt), max_delay)
                        else:
                            delay = base_delay
                        
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_retries} failed: {e}. "
                            f"Retrying in {delay:.1f}s..."
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(f"All {max_retries} attempts failed")
                        raise handle_openai_error(e)
                except AuthenticationError as e:
                    # Не повторяем при ошибке аутентификации
                    raise handle_openai_error(e)
                except Exception as e:
                    # Неизвестные ошибки не повторяем
                    raise handle_openai_error(e)
            
            # Если все попытки исчерпаны
            if last_error:
                raise handle_openai_error(last_error)
        
        return wrapper
    return decorator


class ErrorContext:
    """Контекст для отслеживания ошибок в сессии"""
    
    def __init__(self):
        self.error_count = 0
        self.last_error_time = None
        self.consecutive_errors = 0
    
    def record_error(self):
        """Записать ошибку"""
        import time
        self.error_count += 1
        self.consecutive_errors += 1
        self.last_error_time = time.time()
    
    def record_success(self):
        """Записать успех (сбрасывает consecutive_errors)"""
        self.consecutive_errors = 0
    
    def should_use_fallback(self) -> bool:
        """Проверить, нужно ли использовать fallback"""
        return self.consecutive_errors >= 3
    
    def get_stats(self) -> dict:
        """Получить статистику ошибок"""
        return {
            "total_errors": self.error_count,
            "consecutive_errors": self.consecutive_errors,
            "last_error_time": self.last_error_time,
        }
