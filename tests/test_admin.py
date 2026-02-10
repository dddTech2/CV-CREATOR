"""Tests for admin operations: activate/deactivate users, audit log, drain_usage."""

from unittest.mock import MagicMock, patch

import pytest

from src.auth import AuthManager
from src.token_tracker import TokenTracker, calculate_cost_cop, USER_LIMIT_COP
from src.ai_backend import GeminiClient


# ============================================================
# Fixtures
# ============================================================

FAKE_USER_ID = "user-aaaa-bbbb-cccc-000000000001"
FAKE_ADMIN_ID = "admin-aaaa-bbbb-cccc-000000000002"


@pytest.fixture
def mock_supabase_client():
    """Supabase client mock con tabla chainable."""
    client = MagicMock()

    def _chain(*args, **kwargs):
        return client._query

    client._query = MagicMock()
    client._query.select = MagicMock(return_value=client._query)
    client._query.insert = MagicMock(return_value=client._query)
    client._query.update = MagicMock(return_value=client._query)
    client._query.delete = MagicMock(return_value=client._query)
    client._query.eq = MagicMock(return_value=client._query)
    client._query.order = MagicMock(return_value=client._query)
    client._query.limit = MagicMock(return_value=client._query)

    execute_result = MagicMock()
    execute_result.data = []
    client._query.execute = MagicMock(return_value=execute_result)

    client.table = MagicMock(return_value=client._query)

    return client, execute_result


# ============================================================
# AuthManager: get_all_profiles, set_user_active
# ============================================================


class TestAuthManagerAdmin:
    """Tests for admin-facing AuthManager methods."""

    @patch("src.auth.create_client")
    def test_get_all_profiles(self, mock_create):
        mock_client = MagicMock()
        mock_create.return_value = mock_client

        profiles = [
            {"id": FAKE_USER_ID, "email": "a@a.com", "role": "user", "is_active": True},
            {"id": FAKE_ADMIN_ID, "email": "b@b.com", "role": "admin", "is_active": True},
        ]
        query = MagicMock()
        query.select.return_value = query
        query.order.return_value = query
        execute_result = MagicMock()
        execute_result.data = profiles
        query.execute.return_value = execute_result
        mock_client.table.return_value = query

        AuthManager._client = None
        auth = AuthManager()
        result = auth.get_all_profiles()

        assert len(result) == 2
        assert result[0]["email"] == "a@a.com"
        mock_client.table.assert_called_with("user_profiles")

    @patch("src.auth.create_client")
    def test_get_all_profiles_empty(self, mock_create):
        mock_client = MagicMock()
        mock_create.return_value = mock_client

        query = MagicMock()
        query.select.return_value = query
        query.order.return_value = query
        execute_result = MagicMock()
        execute_result.data = []
        query.execute.return_value = execute_result
        mock_client.table.return_value = query

        AuthManager._client = None
        auth = AuthManager()
        result = auth.get_all_profiles()

        assert result == []

    @patch("src.auth.create_client")
    def test_get_all_profiles_error(self, mock_create):
        mock_client = MagicMock()
        mock_create.return_value = mock_client
        mock_client.table.side_effect = Exception("DB error")

        AuthManager._client = None
        auth = AuthManager()
        result = auth.get_all_profiles()

        assert result == []

    @patch("src.auth.create_client")
    def test_set_user_active_true(self, mock_create):
        mock_client = MagicMock()
        mock_create.return_value = mock_client

        query = MagicMock()
        query.update.return_value = query
        query.eq.return_value = query
        query.execute.return_value = MagicMock()
        mock_client.table.return_value = query

        AuthManager._client = None
        auth = AuthManager()
        result = auth.set_user_active(FAKE_USER_ID, True)

        assert result is True
        mock_client.table.assert_called_with("user_profiles")
        query.update.assert_called_once_with({"is_active": True})

    @patch("src.auth.create_client")
    def test_set_user_active_false(self, mock_create):
        mock_client = MagicMock()
        mock_create.return_value = mock_client

        query = MagicMock()
        query.update.return_value = query
        query.eq.return_value = query
        query.execute.return_value = MagicMock()
        mock_client.table.return_value = query

        AuthManager._client = None
        auth = AuthManager()
        result = auth.set_user_active(FAKE_USER_ID, False)

        assert result is True
        query.update.assert_called_once_with({"is_active": False})

    @patch("src.auth.create_client")
    def test_set_user_active_error(self, mock_create):
        mock_client = MagicMock()
        mock_create.return_value = mock_client
        mock_client.table.side_effect = Exception("DB error")

        AuthManager._client = None
        auth = AuthManager()
        result = auth.set_user_active(FAKE_USER_ID, True)

        assert result is False


# ============================================================
# Admin workflow: activate user (reset tokens + audit log)
# ============================================================


class TestAdminActivateWorkflow:
    """Simulates the full activate/deactivate workflow."""

    @patch("src.token_tracker.create_client")
    def test_activate_user_resets_tokens(self, mock_create):
        """Activar usuario debe resetear tokens."""
        mock_client = MagicMock()
        mock_create.return_value = mock_client

        # Simular que delete retorna 3 registros eliminados
        query = MagicMock()
        query.delete.return_value = query
        query.eq.return_value = query
        delete_result = MagicMock()
        delete_result.data = [{"id": 1}, {"id": 2}, {"id": 3}]
        query.execute.return_value = delete_result
        mock_client.table.return_value = query

        TokenTracker._client = None
        tracker = TokenTracker()
        count = tracker.reset_user_tokens(FAKE_USER_ID)

        assert count == 3
        mock_client.table.assert_called_with("token_usage")

    @patch("src.token_tracker.create_client")
    def test_deactivate_logs_audit(self, mock_create):
        """Desactivar usuario debe crear registro de auditoria."""
        mock_client = MagicMock()
        mock_create.return_value = mock_client

        query = MagicMock()
        query.insert.return_value = query
        query.execute.return_value = MagicMock()
        mock_client.table.return_value = query

        TokenTracker._client = None
        tracker = TokenTracker()
        tracker.log_audit_action(
            user_id=FAKE_USER_ID,
            admin_id=FAKE_ADMIN_ID,
            action="deactivate",
            tokens_at_action=5000,
            cost_at_action_cop=42.0,
            notes="Demo limit reached",
        )

        # Verificar que se inserto en user_audit_log
        call_args = query.insert.call_args[0][0]
        assert call_args["user_id"] == FAKE_USER_ID
        assert call_args["admin_id"] == FAKE_ADMIN_ID
        assert call_args["action"] == "deactivate"
        assert call_args["tokens_at_action"] == 5000
        assert call_args["cost_at_action_cop"] == 42.0
        assert call_args["notes"] == "Demo limit reached"

    @patch("src.token_tracker.create_client")
    def test_activate_logs_audit(self, mock_create):
        """Activar usuario debe crear registro de auditoria."""
        mock_client = MagicMock()
        mock_create.return_value = mock_client

        query = MagicMock()
        query.insert.return_value = query
        query.execute.return_value = MagicMock()
        mock_client.table.return_value = query

        TokenTracker._client = None
        tracker = TokenTracker()
        tracker.log_audit_action(
            user_id=FAKE_USER_ID,
            admin_id=FAKE_ADMIN_ID,
            action="activate",
            tokens_at_action=0,
            cost_at_action_cop=0.0,
        )

        call_args = query.insert.call_args[0][0]
        assert call_args["action"] == "activate"
        assert "notes" not in call_args  # No notes means key not present

    @patch("src.token_tracker.create_client")
    def test_get_audit_log_filtered(self, mock_create):
        """Obtener audit log con filtros."""
        mock_client = MagicMock()
        mock_create.return_value = mock_client

        log_entries = [
            {
                "id": 1,
                "user_id": FAKE_USER_ID,
                "admin_id": FAKE_ADMIN_ID,
                "action": "deactivate",
                "tokens_at_action": 5000,
                "cost_at_action_cop": 42.0,
                "notes": "test",
                "created_at": "2026-01-15T10:00:00",
            },
        ]

        query = MagicMock()
        query.select.return_value = query
        query.order.return_value = query
        query.limit.return_value = query
        query.eq.return_value = query
        execute_result = MagicMock()
        execute_result.data = log_entries
        query.execute.return_value = execute_result
        mock_client.table.return_value = query

        TokenTracker._client = None
        tracker = TokenTracker()
        result = tracker.get_audit_log(user_id=FAKE_USER_ID, action_filter="deactivate")

        assert len(result) == 1
        assert result[0]["action"] == "deactivate"


# ============================================================
# GeminiClient.drain_usage
# ============================================================


class TestGeminiClientDrainUsage:
    """Tests for the usage accumulator on GeminiClient."""

    @patch("src.ai_backend.genai.Client")
    def test_drain_usage_empty(self, mock_genai):
        """drain_usage returns (0,0) when no calls made."""
        mock_genai.return_value = MagicMock()
        client = GeminiClient(api_key="test_key")
        total_in, total_out = client.drain_usage()
        assert total_in == 0
        assert total_out == 0

    @patch("src.ai_backend.genai.Client")
    def test_drain_usage_after_generate(self, mock_genai):
        """drain_usage accumulates tokens from generate() calls."""
        mock_genai_instance = MagicMock()
        mock_genai.return_value = mock_genai_instance

        # Simular respuesta con usage_metadata
        mock_response = MagicMock()
        mock_response.text = "Hello"
        mock_response.usage_metadata = MagicMock()
        mock_response.usage_metadata.prompt_token_count = 100
        mock_response.usage_metadata.candidates_token_count = 50
        mock_genai_instance.models.generate_content.return_value = mock_response

        client = GeminiClient(api_key="test_key")

        # Make 2 calls
        client.generate("test1", retry=False)
        client.generate("test2", retry=False)

        total_in, total_out = client.drain_usage()
        assert total_in == 200  # 100 * 2
        assert total_out == 100  # 50 * 2

    @patch("src.ai_backend.genai.Client")
    def test_drain_usage_clears_after_drain(self, mock_genai):
        """drain_usage clears the accumulator after draining."""
        mock_genai_instance = MagicMock()
        mock_genai.return_value = mock_genai_instance

        mock_response = MagicMock()
        mock_response.text = "Hello"
        mock_response.usage_metadata = MagicMock()
        mock_response.usage_metadata.prompt_token_count = 100
        mock_response.usage_metadata.candidates_token_count = 50
        mock_genai_instance.models.generate_content.return_value = mock_response

        client = GeminiClient(api_key="test_key")
        client.generate("test", retry=False)

        # First drain
        total_in, total_out = client.drain_usage()
        assert total_in == 100
        assert total_out == 50

        # Second drain should be empty
        total_in2, total_out2 = client.drain_usage()
        assert total_in2 == 0
        assert total_out2 == 0

    @patch("src.ai_backend.genai.Client")
    def test_drain_usage_no_metadata(self, mock_genai):
        """drain_usage handles responses without usage_metadata."""
        mock_genai_instance = MagicMock()
        mock_genai.return_value = mock_genai_instance

        mock_response = MagicMock()
        mock_response.text = "Hello"
        mock_response.usage_metadata = None
        mock_genai_instance.models.generate_content.return_value = mock_response

        client = GeminiClient(api_key="test_key")
        client.generate("test", retry=False)

        total_in, total_out = client.drain_usage()
        assert total_in == 0
        assert total_out == 0


# ============================================================
# Integration: cost calculation with COP
# ============================================================


class TestCostCalculation:
    """Verify COP cost formulas."""

    def test_calculate_cost_cop_basic(self):
        """1000 input + 100 output tokens cost calculation."""
        cost = calculate_cost_cop(1000, 100)
        # Input: 1000/1M * 2 * 4200 = 8.4
        # Output: 100/1M * 12 * 4200 = 5.04
        expected = 8.4 + 5.04
        assert abs(cost - expected) < 0.0001

    def test_calculate_cost_cop_zero(self):
        assert calculate_cost_cop(0, 0) == 0.0

    def test_calculate_cost_cop_large(self):
        """1M input + 1M output = (2 + 12) * 4200 = 58800 COP."""
        cost = calculate_cost_cop(1_000_000, 1_000_000)
        assert abs(cost - 58800.0) < 0.01

    def test_user_limit_cop_value(self):
        assert USER_LIMIT_COP == 1500.0

    def test_blocked_threshold(self):
        """A user with >= 1500 COP should be blocked."""
        # 1500 COP / 4200 TRM = ~0.357 USD
        # At $12/M output only: 0.357 / 12 * 1M ≈ 29762 output tokens
        # At $2/M input only: 0.357 / 2 * 1M ≈ 178571 input tokens
        # Just verify the limit constant
        assert USER_LIMIT_COP == 1500.0
