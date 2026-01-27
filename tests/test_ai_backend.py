"""
Tests unitarios para el cliente de Gemini AI (usando nueva API google.genai).
"""
import pytest
from unittest.mock import Mock, patch, MagicMock
from src.ai_backend import (
    GeminiClient,
    CareerStrategist,
    GeminiResponse,
    GeminiClientError,
    GeminiRateLimitError,
    GeminiConnectionError,
)


class TestGeminiClient:
    """Tests para la clase GeminiClient."""

    @patch.dict("os.environ", {"GOOGLE_API_KEY": "test_key"})
    @patch("src.ai_backend.genai.Client")
    def test_init_with_env_var(self, mock_client_class):
        """Test inicialización con variable de entorno."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        client = GeminiClient()

        assert client.api_key == "test_key"
        assert client.model_name == "gemini-2.0-flash-exp"
        mock_client_class.assert_called_once_with(api_key="test_key")

    @patch("src.ai_backend.genai.Client")
    def test_init_with_explicit_key(self, mock_client_class):
        """Test inicialización con API key explícita."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        client = GeminiClient(api_key="explicit_key")

        assert client.api_key == "explicit_key"
        mock_client_class.assert_called_once_with(api_key="explicit_key")

    @patch.dict("os.environ", {}, clear=True)
    def test_init_without_api_key_raises_error(self):
        """Test que falla sin API key."""
        with pytest.raises(GeminiClientError, match="GOOGLE_API_KEY no encontrada"):
            GeminiClient()

    @patch.dict("os.environ", {"GOOGLE_API_KEY": "test_key"})
    @patch("src.ai_backend.genai.Client")
    def test_generate_success(self, mock_client_class):
        """Test generación exitosa de contenido."""
        # Setup mock response
        mock_response = Mock()
        mock_response.text = "Generated response"

        # Setup mock client
        mock_client = Mock()
        mock_client.models.generate_content.return_value = mock_response
        mock_client_class.return_value = mock_client

        # Execute
        client = GeminiClient()
        response = client.generate("Test prompt")

        # Assert
        assert response.success
        assert response.text == "Generated response"
        assert response.error is None
        mock_client.models.generate_content.assert_called_once()

    @patch.dict("os.environ", {"GOOGLE_API_KEY": "test_key"})
    @patch("src.ai_backend.genai.Client")
    def test_generate_with_system_instruction(self, mock_client_class):
        """Test generación con instrucción de sistema."""
        mock_response = Mock()
        mock_response.text = "Response with system"

        mock_client = Mock()
        mock_client.models.generate_content.return_value = mock_response
        mock_client_class.return_value = mock_client

        client = GeminiClient()
        response = client.generate("User prompt", system_instruction="System instruction")

        assert response.success
        # Verificar que se llamó con el prompt completo
        mock_client.models.generate_content.assert_called_once()
        call_args = mock_client.models.generate_content.call_args
        # El contenido debe incluir ambas partes
        assert call_args is not None

    @patch.dict("os.environ", {"GOOGLE_API_KEY": "test_key"})
    @patch("src.ai_backend.genai.Client")
    def test_generate_empty_response(self, mock_client_class):
        """Test con respuesta vacía del modelo."""
        mock_response = Mock()
        mock_response.text = ""

        mock_client = Mock()
        mock_client.models.generate_content.return_value = mock_response
        mock_client_class.return_value = mock_client

        client = GeminiClient()
        response = client.generate("Test prompt")

        assert not response.success
        assert response.text == ""
        assert "vacía" in response.error.lower()

    @patch.dict("os.environ", {"GOOGLE_API_KEY": "test_key"})
    @patch("src.ai_backend.genai.Client")
    @patch("src.ai_backend.time.sleep")
    def test_generate_rate_limit_with_retry(self, mock_sleep, mock_client_class):
        """Test retry en caso de rate limit."""
        mock_client = Mock()
        # Primera llamada falla con rate limit, segunda funciona
        mock_client.models.generate_content.side_effect = [
            Exception("quota exceeded"),
            Mock(text="Success after retry"),
        ]
        mock_client_class.return_value = mock_client

        client = GeminiClient()
        response = client.generate("Test prompt", retry=True)

        assert response.success
        assert response.text == "Success after retry"
        assert mock_client.models.generate_content.call_count == 2
        mock_sleep.assert_called()

    @patch.dict("os.environ", {"GOOGLE_API_KEY": "test_key"})
    @patch("src.ai_backend.genai.Client")
    def test_generate_rate_limit_without_retry(self, mock_client_class):
        """Test sin retry en rate limit."""
        mock_client = Mock()
        mock_client.models.generate_content.side_effect = Exception("rate limit")
        mock_client_class.return_value = mock_client

        client = GeminiClient()
        response = client.generate("Test prompt", retry=False)

        assert not response.success
        assert mock_client.models.generate_content.call_count == 1

    @patch.dict("os.environ", {"GOOGLE_API_KEY": "test_key"})
    @patch("src.ai_backend.genai.Client")
    @patch("src.ai_backend.time.sleep")
    def test_generate_max_retries_exceeded(self, mock_sleep, mock_client_class):
        """Test cuando se exceden los reintentos máximos."""
        mock_client = Mock()
        mock_client.models.generate_content.side_effect = Exception("quota exceeded")
        mock_client_class.return_value = mock_client

        client = GeminiClient()
        response = client.generate("Test prompt", retry=True)

        assert not response.success
        assert mock_client.models.generate_content.call_count == 3  # MAX_RETRIES

    @patch.dict("os.environ", {"GOOGLE_API_KEY": "test_key"})
    @patch("src.ai_backend.genai.Client")
    def test_generate_content_alias(self, mock_client_class):
        """Test método generate_content (alias de generate)."""
        mock_response = Mock()
        mock_response.text = "Generated text"

        mock_client = Mock()
        mock_client.models.generate_content.return_value = mock_response
        mock_client_class.return_value = mock_client

        client = GeminiClient()
        text = client.generate_content("Test prompt")

        assert text == "Generated text"

    @patch.dict("os.environ", {"GOOGLE_API_KEY": "test_key"})
    @patch("src.ai_backend.genai.Client")
    def test_test_connection_success(self, mock_client_class):
        """Test conexión exitosa."""
        mock_response = Mock()
        mock_response.text = "Test"

        mock_client = Mock()
        mock_client.models.generate_content.return_value = mock_response
        mock_client_class.return_value = mock_client

        client = GeminiClient()
        result = client.test_connection()

        assert result is True

    @patch.dict("os.environ", {"GOOGLE_API_KEY": "test_key"})
    @patch("src.ai_backend.genai.Client")
    def test_test_connection_failure(self, mock_client_class):
        """Test fallo de conexión."""
        mock_client = Mock()
        mock_client.models.generate_content.side_effect = Exception("Connection error")
        mock_client_class.return_value = mock_client

        client = GeminiClient()
        result = client.test_connection()

        assert result is False


class TestCareerStrategist:
    """Tests para la clase CareerStrategist."""

    @patch.dict("os.environ", {"GOOGLE_API_KEY": "test_key"})
    @patch("src.ai_backend.genai.Client")
    def test_init_without_client(self, mock_client_class):
        """Test inicialización sin cliente explícito."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        strategist = CareerStrategist()

        assert strategist.client is not None
        assert isinstance(strategist.client, GeminiClient)

    @patch.dict("os.environ", {"GOOGLE_API_KEY": "test_key"})
    @patch("src.ai_backend.genai.Client")
    def test_init_with_client(self, mock_client_class):
        """Test inicialización con cliente explícito."""
        mock_genai_client = Mock()
        mock_client_class.return_value = mock_genai_client

        custom_client = GeminiClient()
        strategist = CareerStrategist(client=custom_client)

        assert strategist.client == custom_client

    @patch.dict("os.environ", {"GOOGLE_API_KEY": "test_key"})
    @patch("src.ai_backend.genai.Client")
    def test_analyze_gap(self, mock_client_class):
        """Test análisis de brechas."""
        mock_response = Mock()
        mock_response.text = "Gap analysis questions"

        mock_client = Mock()
        mock_client.models.generate_content.return_value = mock_response
        mock_client_class.return_value = mock_client

        strategist = CareerStrategist()
        response = strategist.analyze_gap(
            cv_text="My CV", job_description="Job description", language="es"
        )

        assert response.success
        assert "Gap analysis questions" in response.text

    @patch.dict("os.environ", {"GOOGLE_API_KEY": "test_key"})
    @patch("src.ai_backend.genai.Client")
    def test_generate_yaml(self, mock_client_class):
        """Test generación de YAML."""
        mock_response = Mock()
        mock_response.text = "```yaml\ncv:\n  name: Test\n```"

        mock_client = Mock()
        mock_client.models.generate_content.return_value = mock_response
        mock_client_class.return_value = mock_client

        strategist = CareerStrategist()
        response = strategist.generate_yaml(
            cv_text="My CV",
            job_description="Job desc",
            user_answers="My answers",
            language="es",
            yaml_template="template",
        )

        assert response.success
        # Debe extraer el YAML limpio
        assert "cv:" in response.text
        assert "```" not in response.text

    @patch.dict("os.environ", {"GOOGLE_API_KEY": "test_key"})
    @patch("src.ai_backend.genai.Client")
    def test_extract_yaml_with_markers(self, mock_client_class):
        """Test extracción de YAML con marcadores."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        strategist = CareerStrategist()

        text_with_markers = "Some text\n```yaml\ncv:\n  name: Test\n```\nMore text"
        extracted = strategist._extract_yaml(text_with_markers)

        assert extracted == "cv:\n  name: Test"
        assert "```" not in extracted

    @patch.dict("os.environ", {"GOOGLE_API_KEY": "test_key"})
    @patch("src.ai_backend.genai.Client")
    def test_extract_yaml_without_markers(self, mock_client_class):
        """Test extracción de YAML sin marcadores."""
        mock_client = Mock()
        mock_client_class.return_value = mock_client

        strategist = CareerStrategist()

        text_without_markers = "cv:\n  name: Test"
        extracted = strategist._extract_yaml(text_without_markers)

        assert extracted == "cv:\n  name: Test"


class TestGeminiResponse:
    """Tests para la clase GeminiResponse."""

    def test_response_creation(self):
        """Test creación de respuesta."""
        response = GeminiResponse(text="Test", success=True)

        assert response.text == "Test"
        assert response.success is True
        assert response.error is None
        assert response.model_used is None

    def test_response_with_error(self):
        """Test respuesta con error."""
        response = GeminiResponse(text="", success=False, error="Test error")

        assert response.text == ""
        assert response.success is False
        assert response.error == "Test error"
