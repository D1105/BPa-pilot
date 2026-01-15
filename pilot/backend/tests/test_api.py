"""
Integration тесты для API
"""
import pytest
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Добавляем путь к backend
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi.testclient import TestClient
from httpx import AsyncClient, ASGITransport
import asyncio


# Мокаем зависимости до импорта main
@pytest.fixture(scope="module")
def mock_dependencies():
    """Мокаем внешние зависимости"""
    with patch('agent.ChatOpenAI') as mock_llm, \
         patch('simulator.ChatOpenAI') as mock_sim_llm:
        
        # Мок для agent
        mock_instance = MagicMock()
        mock_instance.ainvoke = AsyncMock(return_value=MagicMock(content='{"car_brand": null}'))
        mock_llm.return_value = mock_instance
        
        # Мок для simulator
        mock_sim_instance = MagicMock()
        mock_sim_instance.ainvoke = AsyncMock(return_value=MagicMock(content="Здравствуйте"))
        mock_sim_llm.return_value = mock_sim_instance
        
        yield


@pytest.fixture
def client(mock_dependencies):
    """Тестовый клиент"""
    from main import app
    return TestClient(app)


class TestHealthEndpoints:
    """Тесты health endpoints"""
    
    def test_root_endpoint(self, client):
        """Тест корневого эндпоинта"""
        response = client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ok"
        assert "АвтоИмпорт" in data["service"]
    
    def test_health_endpoint(self, client):
        """Тест health check"""
        response = client.get("/health")
        
        assert response.status_code in [200, 503]
        data = response.json()
        assert "status" in data


class TestChatAPI:
    """Тесты Chat API"""
    
    def test_chat_endpoint_success(self, client, mock_dependencies):
        """Тест успешного запроса к чату"""
        with patch('main.agent') as mock_agent:
            mock_agent.process_message = AsyncMock(return_value={
                "response": "Здравствуйте! Чем могу помочь?",
                "session_id": "test123",
                "extracted_data": {},
                "lead_status": "discovery",
            })
            
            response = client.post("/api/chat", json={
                "message": "Привет",
                "history": [],
            })
        
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert "session_id" in data
    
    def test_chat_endpoint_empty_message(self, client):
        """Тест: пустое сообщение возвращает ошибку валидации"""
        response = client.post("/api/chat", json={
            "message": "",
            "history": [],
        })
        
        assert response.status_code == 422  # Validation error
    
    def test_chat_endpoint_with_history(self, client, mock_dependencies):
        """Тест чата с историей"""
        with patch('main.agent') as mock_agent:
            mock_agent.process_message = AsyncMock(return_value={
                "response": "Понял, ищете Toyota",
                "session_id": "test123",
                "extracted_data": {"car_brand": "Toyota"},
                "lead_status": "qualification",
            })
            
            response = client.post("/api/chat", json={
                "message": "Хочу Toyota",
                "history": [
                    {"role": "assistant", "content": "Здравствуйте!"},
                    {"role": "user", "content": "Привет"},
                ],
                "session_id": "test123",
            })
        
        assert response.status_code == 200
        data = response.json()
        assert data["session_id"] == "test123"
    
    def test_chat_endpoint_long_message(self, client, mock_dependencies):
        """Тест: длинное сообщение обрабатывается"""
        with patch('main.agent') as mock_agent:
            mock_agent.process_message = AsyncMock(return_value={
                "response": "OK",
                "session_id": "test123",
                "extracted_data": {},
                "lead_status": "discovery",
            })
            
            long_message = "a" * 1500  # Меньше лимита 2000
            response = client.post("/api/chat", json={
                "message": long_message,
                "history": [],
            })
        
        assert response.status_code == 200


class TestLeadsAPI:
    """Тесты Leads API"""
    
    def test_get_leads_empty(self, client):
        """Тест: получение пустого списка лидов"""
        response = client.get("/api/leads")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
    
    def test_get_lead_not_found(self, client):
        """Тест: лид не найден"""
        response = client.get("/api/leads/nonexistent123")
        
        assert response.status_code == 404
    
    def test_get_conversation_empty(self, client):
        """Тест: получение пустой истории диалога"""
        response = client.get("/api/conversations/test123")
        
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


class TestStatsAPI:
    """Тесты Stats API"""
    
    def test_get_stats(self, client):
        """Тест: получение статистики"""
        response = client.get("/api/stats")
        
        assert response.status_code == 200
        data = response.json()
        assert "total_leads" in data
        assert "hot_leads" in data
        assert "warm_leads" in data
        assert "cold_leads" in data


class TestSimulatorAPI:
    """Тесты Simulator API"""
    
    def test_get_presets(self, client):
        """Тест: получение пресетов"""
        response = client.get("/api/simulator/presets")
        
        assert response.status_code == 200
        data = response.json()
        assert "presets" in data
        assert len(data["presets"]) == 4
        
        preset_ids = [p["id"] for p in data["presets"]]
        assert "easy" in preset_ids
        assert "medium" in preset_ids
        assert "hard" in preset_ids
        assert "nightmare" in preset_ids
    
    def test_simulator_chat_success(self, client, mock_dependencies):
        """Тест: успешный чат с симулятором"""
        with patch('main.simulator') as mock_sim:
            mock_sim.process_message = AsyncMock(return_value={
                "response": "Здравствуйте, хочу BMW",
                "session_id": "sim123",
            })
            
            response = client.post("/api/simulator/chat", json={
                "message": "Добрый день!",
                "history": [],
                "preset": "medium",
            })
        
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert "session_id" in data
        assert "persona_name" in data
    
    def test_simulator_chat_with_preset(self, client, mock_dependencies):
        """Тест: чат с конкретным пресетом"""
        with patch('main.simulator') as mock_sim:
            mock_sim.process_message = AsyncMock(return_value={
                "response": "Чё надо?",
                "session_id": "sim123",
            })
            
            response = client.post("/api/simulator/chat", json={
                "message": "Здравствуйте",
                "history": [],
                "preset": "nightmare",
            })
        
        assert response.status_code == 200
        data = response.json()
        assert data["persona_name"] == "nightmare"
    
    def test_simulator_chat_invalid_preset(self, client):
        """Тест: невалидный пресет"""
        response = client.post("/api/simulator/chat", json={
            "message": "Привет",
            "history": [],
            "preset": "invalid_preset",
        })
        
        assert response.status_code == 422  # Validation error
    
    def test_simulator_evaluate_success(self, client, mock_dependencies):
        """Тест: успешная оценка"""
        with patch('main.simulator') as mock_sim:
            mock_sim.evaluate_session = AsyncMock(return_value={
                "scores": {
                    "contact": 70,
                    "needs_discovery": 80,
                    "objection_handling": 60,
                    "presentation": 75,
                    "closing": 50
                },
                "strengths": ["Хороший контакт"],
                "improvements": ["Закрытие"],
                "overall_score": 67,
                "recommendations": "Практикуйтесь"
            })
            
            response = client.post("/api/simulator/evaluate", json={
                "history": [
                    {"role": "manager", "content": "Добрый день!"},
                    {"role": "client", "content": "Здравствуйте"},
                ],
                "preset": "medium",
            })
        
        assert response.status_code == 200
        data = response.json()
        assert "scores" in data
        assert "overall_score" in data
    
    def test_simulator_evaluate_short_history(self, client):
        """Тест: оценка с короткой историей"""
        response = client.post("/api/simulator/evaluate", json={
            "history": [
                {"role": "manager", "content": "Привет"},
            ],
            "preset": "medium",
        })
        
        assert response.status_code == 422  # Validation error - min_items=2


class TestErrorHandling:
    """Тесты обработки ошибок"""
    
    def test_chat_graceful_error(self, client, mock_dependencies):
        """Тест: graceful degradation при ошибке чата"""
        with patch('main.agent') as mock_agent:
            mock_agent.process_message = AsyncMock(
                side_effect=Exception("Test error")
            )
            
            response = client.post("/api/chat", json={
                "message": "Привет",
                "history": [],
            })
        
        # Должен вернуть 200 с fallback ответом
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert "error" in data or data["response"]  # Либо ошибка, либо fallback
    
    def test_simulator_graceful_error(self, client, mock_dependencies):
        """Тест: graceful degradation при ошибке симулятора"""
        with patch('main.simulator') as mock_sim:
            mock_sim.process_message = AsyncMock(
                side_effect=Exception("Test error")
            )
            
            response = client.post("/api/simulator/chat", json={
                "message": "Привет",
                "history": [],
                "preset": "medium",
            })
        
        # Должен вернуть 200 с fallback ответом
        assert response.status_code == 200
        data = response.json()
        assert "response" in data


class TestValidation:
    """Тесты валидации входных данных"""
    
    def test_chat_message_max_length(self, client):
        """Тест: превышение максимальной длины сообщения"""
        response = client.post("/api/chat", json={
            "message": "a" * 2001,  # Больше лимита
            "history": [],
        })
        
        assert response.status_code == 422
    
    def test_simulator_message_max_length(self, client):
        """Тест: превышение максимальной длины в симуляторе"""
        response = client.post("/api/simulator/chat", json={
            "message": "a" * 1001,  # Больше лимита 1000
            "history": [],
            "preset": "medium",
        })
        
        assert response.status_code == 422
