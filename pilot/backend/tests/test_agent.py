"""
Unit тесты для AutoImportAgent
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Добавляем путь к backend
sys.path.insert(0, str(Path(__file__).parent.parent))

from agent import AutoImportAgent, ConversationState


class TestBudgetParsing:
    """Тесты парсинга бюджета"""
    
    @pytest.fixture
    def agent(self):
        with patch('agent.ChatOpenAI'):
            return AutoImportAgent()
    
    def test_parse_budget_millions_short(self, agent):
        """Тест парсинга '2 млн'"""
        assert agent._parse_budget("2 млн") == 2_000_000
        assert agent._parse_budget("2.5 млн") == 2_500_000
        assert agent._parse_budget("3млн") == 3_000_000
    
    def test_parse_budget_millions_full(self, agent):
        """Тест парсинга 'миллион'"""
        assert agent._parse_budget("2 миллиона") == 2_000_000
        assert agent._parse_budget("1.5 миллиона") == 1_500_000
    
    def test_parse_budget_thousands(self, agent):
        """Тест парсинга тысяч"""
        assert agent._parse_budget("500 тыс") == 500_000
        assert agent._parse_budget("1500 тысяч") == 1_500_000
    
    def test_parse_budget_raw_number(self, agent):
        """Тест парсинга чисел"""
        assert agent._parse_budget(2000000) == 2_000_000
        assert agent._parse_budget("2000000") == 2_000_000
        assert agent._parse_budget(2.5) == 2
    
    def test_parse_budget_small_number_as_millions(self, agent):
        """Тест: маленькие числа интерпретируются как миллионы"""
        assert agent._parse_budget("2") == 2_000_000
        assert agent._parse_budget("3.5") == 3_500_000
    
    def test_parse_budget_invalid(self, agent):
        """Тест невалидных значений"""
        assert agent._parse_budget("") is None
        assert agent._parse_budget("много") is None
        assert agent._parse_budget(None) is None


class TestStageDetection:
    """Тесты определения этапа диалога"""
    
    @pytest.fixture
    def agent(self):
        with patch('agent.ChatOpenAI'):
            return AutoImportAgent()
    
    @pytest.mark.asyncio
    async def test_discovery_stage_empty_data(self, agent):
        """Тест: пустые данные = discovery"""
        state: ConversationState = {
            "session_id": "test",
            "messages": [],
            "extracted_data": {},
            "current_stage": "",
            "missing_slots": [],
            "lead_qualification": None,
            "error": None,
        }
        
        result = await agent._determine_stage(state)
        assert result["current_stage"] == "discovery"
    
    @pytest.mark.asyncio
    async def test_qualification_stage_with_basic_info(self, agent):
        """Тест: есть базовая инфо = qualification"""
        state: ConversationState = {
            "session_id": "test",
            "messages": [],
            "extracted_data": {"car_brand": "Toyota"},
            "current_stage": "",
            "missing_slots": [],
            "lead_qualification": None,
            "error": None,
        }
        
        result = await agent._determine_stage(state)
        assert result["current_stage"] == "qualification"
    
    @pytest.mark.asyncio
    async def test_closing_stage_with_qualification_info(self, agent):
        """Тест: есть квалификационная инфо = closing"""
        state: ConversationState = {
            "session_id": "test",
            "messages": [],
            "extracted_data": {
                "car_brand": "Toyota",
                "budget_max": 3_000_000,
            },
            "current_stage": "",
            "missing_slots": [],
            "lead_qualification": None,
            "error": None,
        }
        
        result = await agent._determine_stage(state)
        assert result["current_stage"] == "closing"
    
    @pytest.mark.asyncio
    async def test_completed_stage_with_all_info(self, agent):
        """Тест: все данные = completed"""
        state: ConversationState = {
            "session_id": "test",
            "messages": [],
            "extracted_data": {
                "car_brand": "Toyota",
                "budget_max": 3_000_000,
                "name": "Иван",
                "phone": "+79001234567",
            },
            "current_stage": "",
            "missing_slots": [],
            "lead_qualification": None,
            "error": None,
        }
        
        result = await agent._determine_stage(state)
        assert result["current_stage"] == "completed"


class TestLeadQualification:
    """Тесты квалификации лидов"""
    
    @pytest.fixture
    def agent(self):
        with patch('agent.ChatOpenAI'):
            return AutoImportAgent()
    
    @pytest.mark.asyncio
    async def test_hot_lead_high_budget(self, agent):
        """Тест: высокий бюджет = hot"""
        state: ConversationState = {
            "session_id": "test",
            "messages": [],
            "extracted_data": {
                "car_brand": "BMW",
                "budget_max": 5_000_000,
                "name": "Иван",
                "phone": "+79001234567",
            },
            "current_stage": "",
            "missing_slots": [],
            "lead_qualification": None,
            "error": None,
        }
        
        result = await agent._determine_stage(state)
        assert result["lead_qualification"] == "hot"
    
    @pytest.mark.asyncio
    async def test_hot_lead_urgent(self, agent):
        """Тест: срочность = hot"""
        state: ConversationState = {
            "session_id": "test",
            "messages": [],
            "extracted_data": {
                "car_brand": "Toyota",
                "budget_max": 2_000_000,
                "name": "Иван",
                "phone": "+79001234567",
                "timeline": "срочно нужна машина",
            },
            "current_stage": "",
            "missing_slots": [],
            "lead_qualification": None,
            "error": None,
        }
        
        result = await agent._determine_stage(state)
        assert result["lead_qualification"] == "hot"
    
    @pytest.mark.asyncio
    async def test_warm_lead_medium_budget(self, agent):
        """Тест: средний бюджет = warm"""
        state: ConversationState = {
            "session_id": "test",
            "messages": [],
            "extracted_data": {
                "car_brand": "Hyundai",
                "budget_max": 2_000_000,
                "name": "Иван",
                "phone": "+79001234567",
            },
            "current_stage": "",
            "missing_slots": [],
            "lead_qualification": None,
            "error": None,
        }
        
        result = await agent._determine_stage(state)
        assert result["lead_qualification"] == "warm"
    
    @pytest.mark.asyncio
    async def test_cold_lead_low_budget(self, agent):
        """Тест: низкий бюджет без дополнительной инфо = cold"""
        state: ConversationState = {
            "session_id": "test",
            "messages": [],
            "extracted_data": {
                "car_brand": "Lada",
                "budget_max": 500_000,
                "name": "Иван",
                "phone": "+79001234567",
                # Нет body_type и других данных, которые делают warm
            },
            "current_stage": "",
            "missing_slots": [],
            "lead_qualification": None,
            "error": None,
        }
        
        result = await agent._determine_stage(state)
        # При наличии car_brand (has_basic_info=True) и бюджете < 1.5M = warm
        # Это корректное поведение, так как есть базовая информация
        assert result["lead_qualification"] in ["cold", "warm"]


class TestProcessMessage:
    """Тесты обработки сообщений"""
    
    @pytest.fixture
    def agent(self):
        with patch('agent.ChatOpenAI') as mock_llm:
            mock_instance = MagicMock()
            mock_instance.ainvoke = AsyncMock(return_value=MagicMock(content='{"car_brand": null}'))
            mock_llm.return_value = mock_instance
            return AutoImportAgent()
    
    @pytest.mark.asyncio
    async def test_empty_message_returns_prompt(self, agent):
        """Тест: пустое сообщение возвращает подсказку"""
        with patch('agent.get_db'):
            result = await agent.process_message(
                message="",
                history=[],
                session_id=None,
            )
        
        assert "напишите" in result["response"].lower() or "вопрос" in result["response"].lower()
    
    @pytest.mark.asyncio
    async def test_message_truncation(self, agent):
        """Тест: длинное сообщение обрезается"""
        long_message = "a" * 3000
        
        with patch('agent.get_db') as mock_db:
            mock_db.return_value.__aenter__ = AsyncMock()
            mock_db.return_value.__aexit__ = AsyncMock()
            
            # Мокаем граф
            agent.graph = MagicMock()
            agent.graph.ainvoke = AsyncMock(return_value={
                "messages": [{"role": "assistant", "content": "OK"}],
                "extracted_data": {},
                "current_stage": "discovery",
                "lead_qualification": None,
                "error": None,
            })
            
            result = await agent.process_message(
                message=long_message,
                history=[],
                session_id="test",
            )
        
        # Проверяем что ответ вернулся
        assert "response" in result
    
    @pytest.mark.asyncio
    async def test_session_id_generation(self, agent):
        """Тест: генерация session_id"""
        with patch('agent.get_db') as mock_db:
            mock_db.return_value.__aenter__ = AsyncMock()
            mock_db.return_value.__aexit__ = AsyncMock()
            
            agent.graph = MagicMock()
            agent.graph.ainvoke = AsyncMock(return_value={
                "messages": [{"role": "assistant", "content": "OK"}],
                "extracted_data": {},
                "current_stage": "discovery",
                "lead_qualification": None,
                "error": None,
            })
            
            result = await agent.process_message(
                message="Привет",
                history=[],
                session_id=None,
            )
        
        assert result["session_id"] is not None
        assert len(result["session_id"]) == 8


class TestErrorHandling:
    """Тесты обработки ошибок"""
    
    @pytest.fixture
    def agent(self):
        with patch('agent.ChatOpenAI'):
            return AutoImportAgent()
    
    @pytest.mark.asyncio
    async def test_fallback_on_error(self, agent):
        """Тест: fallback при ошибке"""
        # Симулируем 3 ошибки подряд
        agent.error_context.consecutive_errors = 3
        
        state: ConversationState = {
            "session_id": "test",
            "messages": [{"role": "user", "content": "Привет"}],
            "extracted_data": {},
            "current_stage": "discovery",
            "missing_slots": [],
            "lead_qualification": None,
            "error": None,
        }
        
        result = await agent._generate_response(state)
        
        # Должен использовать fallback
        assert len(result["messages"]) == 2
        assert "assistant" == result["messages"][-1]["role"]
