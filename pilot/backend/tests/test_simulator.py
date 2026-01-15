"""
Unit тесты для ClientSimulator
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Добавляем путь к backend
sys.path.insert(0, str(Path(__file__).parent.parent))

from simulator import ClientSimulator, ClientPersona


class TestClientPersona:
    """Тесты модели персоны клиента"""
    
    def test_default_persona(self):
        """Тест дефолтной персоны"""
        persona = ClientPersona()
        
        assert persona.cooperativeness == 5
        assert persona.rudeness == 3
        assert persona.budget_flexibility == 5
        assert persona.urgency == 5
        assert persona.knowledge_level == 5
        assert persona.decisiveness == 5
        assert persona.trust_level == 5
    
    def test_custom_persona(self):
        """Тест кастомной персоны"""
        persona = ClientPersona(
            cooperativeness=1,
            rudeness=10,
            desired_car="Porsche 911",
            budget_range="10 млн",
        )
        
        assert persona.cooperativeness == 1
        assert persona.rudeness == 10
        assert persona.desired_car == "Porsche 911"
        assert persona.budget_range == "10 млн"


class TestPresets:
    """Тесты пресетов клиентов"""
    
    def test_easy_preset_exists(self):
        """Тест: пресет easy существует"""
        assert "easy" in ClientSimulator.PERSONA_PRESETS
        
        easy = ClientSimulator.PERSONA_PRESETS["easy"]
        assert easy.cooperativeness >= 7
        assert easy.rudeness <= 3
    
    def test_medium_preset_exists(self):
        """Тест: пресет medium существует"""
        assert "medium" in ClientSimulator.PERSONA_PRESETS
        
        medium = ClientSimulator.PERSONA_PRESETS["medium"]
        assert 4 <= medium.cooperativeness <= 6
    
    def test_hard_preset_exists(self):
        """Тест: пресет hard существует"""
        assert "hard" in ClientSimulator.PERSONA_PRESETS
        
        hard = ClientSimulator.PERSONA_PRESETS["hard"]
        assert hard.cooperativeness <= 4
        assert hard.knowledge_level >= 7
    
    def test_nightmare_preset_exists(self):
        """Тест: пресет nightmare существует"""
        assert "nightmare" in ClientSimulator.PERSONA_PRESETS
        
        nightmare = ClientSimulator.PERSONA_PRESETS["nightmare"]
        assert nightmare.cooperativeness <= 2
        assert nightmare.rudeness >= 8
        assert nightmare.trust_level <= 2


class TestSystemPrompt:
    """Тесты генерации системного промпта"""
    
    @pytest.fixture
    def simulator(self):
        with patch('simulator.ChatOpenAI'):
            return ClientSimulator()
    
    def test_prompt_contains_persona_info(self, simulator):
        """Тест: промпт содержит информацию о персоне"""
        persona = ClientPersona(
            desired_car="BMW X5",
            budget_range="5 млн",
            country_preference="Германия",
        )
        
        prompt = simulator._build_system_prompt(persona)
        
        assert "BMW X5" in prompt
        assert "5 млн" in prompt
        assert "Германия" in prompt
    
    def test_prompt_contains_hidden_objections(self, simulator):
        """Тест: промпт содержит скрытые возражения"""
        persona = ClientPersona(
            hidden_objections=["боюсь обмана", "жена против"]
        )
        
        prompt = simulator._build_system_prompt(persona)
        
        assert "боюсь обмана" in prompt
        assert "жена против" in prompt
    
    def test_prompt_contains_buying_triggers(self, simulator):
        """Тест: промпт содержит триггеры покупки"""
        persona = ClientPersona(
            buying_triggers=["гарантия", "скидка"]
        )
        
        prompt = simulator._build_system_prompt(persona)
        
        assert "гарантия" in prompt
        assert "скидка" in prompt
    
    def test_prompt_rudeness_description(self, simulator):
        """Тест: промпт содержит описание грубости"""
        rude_persona = ClientPersona(rudeness=9)
        polite_persona = ClientPersona(rudeness=1)
        
        rude_prompt = simulator._build_system_prompt(rude_persona)
        polite_prompt = simulator._build_system_prompt(polite_persona)
        
        assert "хам" in rude_prompt.lower()
        assert "вежлив" in polite_prompt.lower()


class TestProcessMessage:
    """Тесты обработки сообщений"""
    
    @pytest.fixture
    def simulator(self):
        with patch('simulator.ChatOpenAI') as mock_llm:
            mock_instance = MagicMock()
            mock_instance.ainvoke = AsyncMock(
                return_value=MagicMock(content="Здравствуйте, хочу BMW")
            )
            mock_llm.return_value = mock_instance
            return ClientSimulator()
    
    @pytest.mark.asyncio
    async def test_empty_message_returns_dots(self, simulator):
        """Тест: пустое сообщение возвращает '...'"""
        result = await simulator.process_message(
            message="",
            persona=ClientPersona(),
            history=[],
        )
        
        assert result["response"] == "..."
    
    @pytest.mark.asyncio
    async def test_session_id_generation(self, simulator):
        """Тест: генерация session_id"""
        result = await simulator.process_message(
            message="Добрый день",
            persona=ClientPersona(),
            history=[],
            session_id=None,
        )
        
        assert result["session_id"] is not None
        assert len(result["session_id"]) == 8
    
    @pytest.mark.asyncio
    async def test_session_id_preserved(self, simulator):
        """Тест: session_id сохраняется"""
        result = await simulator.process_message(
            message="Добрый день",
            persona=ClientPersona(),
            history=[],
            session_id="test1234",
        )
        
        assert result["session_id"] == "test1234"


class TestEvaluation:
    """Тесты оценки сессии"""
    
    @pytest.fixture
    def simulator(self):
        with patch('simulator.ChatOpenAI') as mock_llm:
            mock_instance = MagicMock()
            mock_instance.ainvoke = AsyncMock(return_value=MagicMock(content='''
{
  "scores": {
    "contact": 70,
    "needs_discovery": 80,
    "objection_handling": 60,
    "presentation": 75,
    "closing": 50
  },
  "strengths": ["Хороший контакт", "Правильные вопросы"],
  "improvements": ["Работа с возражениями", "Закрытие сделки"],
  "overall_score": 67,
  "recommendations": "Больше практики"
}
'''))
            mock_llm.return_value = mock_instance
            return ClientSimulator()
    
    @pytest.mark.asyncio
    async def test_evaluation_returns_scores(self, simulator):
        """Тест: оценка возвращает баллы"""
        history = [
            {"role": "manager", "content": "Добрый день!"},
            {"role": "client", "content": "Здравствуйте"},
            {"role": "manager", "content": "Чем могу помочь?"},
            {"role": "client", "content": "Хочу машину"},
        ]
        
        result = await simulator.evaluate_session(
            persona=ClientPersona(),
            history=history,
        )
        
        assert "scores" in result
        assert "overall_score" in result
        assert "strengths" in result
        assert "improvements" in result
        assert "recommendations" in result
    
    @pytest.mark.asyncio
    async def test_evaluation_validates_structure(self, simulator):
        """Тест: валидация структуры оценки"""
        valid = {
            "scores": {
                "contact": 50,
                "needs_discovery": 50,
                "objection_handling": 50,
                "presentation": 50,
                "closing": 50
            },
            "strengths": ["a"],
            "improvements": ["b"],
            "overall_score": 50,
            "recommendations": "c"
        }
        
        assert simulator._validate_evaluation(valid) is True
    
    @pytest.mark.asyncio
    async def test_evaluation_rejects_invalid(self, simulator):
        """Тест: отклонение невалидной структуры"""
        invalid = {"scores": {}}
        
        assert simulator._validate_evaluation(invalid) is False
    
    @pytest.mark.asyncio
    async def test_default_evaluation(self, simulator):
        """Тест: дефолтная оценка"""
        result = simulator._get_default_evaluation("Тестовая причина")
        
        assert result["overall_score"] == 50
        assert "Тестовая причина" in result["improvements"]
    
    @pytest.mark.asyncio
    async def test_evaluation_with_short_history(self, simulator):
        """Тест: оценка с короткой историей"""
        history = [
            {"role": "manager", "content": "Привет"},
        ]
        
        result = await simulator.evaluate_session(
            persona=ClientPersona(),
            history=history,
        )
        
        # Должен вернуть дефолтную оценку
        assert result["overall_score"] == 50
        assert "Недостаточно данных" in result["improvements"][0]


class TestErrorHandling:
    """Тесты обработки ошибок"""
    
    @pytest.fixture
    def simulator(self):
        with patch('simulator.ChatOpenAI'):
            return ClientSimulator()
    
    @pytest.mark.asyncio
    async def test_fallback_on_consecutive_errors(self, simulator):
        """Тест: fallback при последовательных ошибках"""
        simulator.error_context.consecutive_errors = 3
        
        result = await simulator.process_message(
            message="Привет",
            persona=ClientPersona(),
            history=[],
        )
        
        assert "недоступен" in result["response"].lower() or "попробуйте" in result["response"].lower()
