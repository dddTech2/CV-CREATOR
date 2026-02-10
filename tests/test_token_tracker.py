"""
Tests para el modulo de tracking de tokens (src/token_tracker.py).

Todos los tests usan mocks del cliente Supabase.
"""

import os
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from src.token_tracker import (
    INPUT_PRICE_USD_PER_M,
    OUTPUT_PRICE_USD_PER_M,
    TRM_COP_USD,
    USER_LIMIT_COP,
    CVUsageSummary,
    TokenRecord,
    TokenTracker,
    calculate_cost_cop,
)

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


class MockResponse:
    """Simula la respuesta del SDK de Supabase."""

    def __init__(self, data: list | None = None):
        self.data: list = data if data is not None else []


def _make_chain(response_data: list | None = None) -> MagicMock:
    """Crea un mock encadenable que simula queries de Supabase."""
    chain = MagicMock()
    for method in ("select", "insert", "delete", "eq", "order", "limit"):
        getattr(chain, method).return_value = chain
    chain.execute.return_value = MockResponse(response_data)
    return chain


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_singleton():
    """Reset singleton antes y despues de cada test."""
    TokenTracker._client = None
    yield
    TokenTracker._client = None


@pytest.fixture()
def mock_client():
    """Proporciona un mock del cliente Supabase con env vars configuradas."""
    with (
        patch.dict(
            os.environ,
            {
                "SUPABASE_URL": "https://test-project.supabase.co",
                "SUPABASE_KEY": "test-anon-key-1234567890",
            },
        ),
        patch("src.token_tracker.create_client") as mock_create,
    ):
        client = MagicMock()
        mock_create.return_value = client
        yield client


@pytest.fixture()
def tracker(mock_client: MagicMock) -> TokenTracker:
    """Instancia de TokenTracker con cliente mockeado."""
    return TokenTracker()


# ------------------------------------------------------------------
# Tests: calculate_cost_cop
# ------------------------------------------------------------------


class TestCalculateCostCop:
    def test_basic_calculation(self):
        """Verifica la formula: (in/1M * 2 + out/1M * 12) * 4200."""
        cost = calculate_cost_cop(1_000_000, 1_000_000)
        expected = (2.00 + 12.00) * 4200
        assert cost == pytest.approx(expected)

    def test_zero_tokens(self):
        cost = calculate_cost_cop(0, 0)
        assert cost == 0.0

    def test_input_only(self):
        cost = calculate_cost_cop(1_000_000, 0)
        expected = 2.00 * 4200
        assert cost == pytest.approx(expected)

    def test_output_only(self):
        cost = calculate_cost_cop(0, 1_000_000)
        expected = 12.00 * 4200
        assert cost == pytest.approx(expected)

    def test_small_amounts(self):
        """1000 input + 100 output tokens."""
        cost = calculate_cost_cop(1000, 100)
        expected = (1000 / 1_000_000 * 2.00 + 100 / 1_000_000 * 12.00) * 4200
        assert cost == pytest.approx(expected)

    def test_prd_example(self):
        """Verificar formula del PRD: cost_cop = (in/1M*2 + out/1M*12) * 4200."""
        in_tokens = 10_000
        out_tokens = 5_000
        cost = calculate_cost_cop(in_tokens, out_tokens)
        expected = (10_000 / 1_000_000 * 2.00 + 5_000 / 1_000_000 * 12.00) * 4200
        assert cost == pytest.approx(expected)


# ------------------------------------------------------------------
# Tests: Constantes
# ------------------------------------------------------------------


class TestConstants:
    def test_input_price(self):
        assert INPUT_PRICE_USD_PER_M == 2.00

    def test_output_price(self):
        assert OUTPUT_PRICE_USD_PER_M == 12.00

    def test_trm(self):
        assert TRM_COP_USD == 4200.0

    def test_user_limit(self):
        assert USER_LIMIT_COP == 1500.0


# ------------------------------------------------------------------
# Tests: TokenTracker init
# ------------------------------------------------------------------


class TestTokenTrackerInit:
    def test_init_creates_client(self, mock_client: MagicMock):
        tracker = TokenTracker()
        assert tracker.client is mock_client

    def test_init_missing_env_vars(self):
        with (
            patch.dict(os.environ, {}, clear=True),
            pytest.raises(ValueError, match="SUPABASE_URL"),
        ):
            TokenTracker()

    def test_init_singleton(self, mock_client: MagicMock):
        t1 = TokenTracker()
        t2 = TokenTracker()
        assert t1.client is t2.client


# ------------------------------------------------------------------
# Tests: record_usage
# ------------------------------------------------------------------


class TestRecordUsage:
    def test_record_usage_basic(self, tracker: TokenTracker, mock_client: MagicMock):
        chain = _make_chain([{"id": 1}])
        mock_client.table.return_value = chain

        record = tracker.record_usage(
            user_id="user-123",
            operation="gap_analysis",
            input_tokens=1000,
            output_tokens=500,
        )

        assert isinstance(record, TokenRecord)
        assert record.operation == "gap_analysis"
        assert record.input_tokens == 1000
        assert record.output_tokens == 500
        assert record.total_cost_cop > 0
        mock_client.table.assert_called_with("token_usage")

    def test_record_usage_cost_calculation(self, tracker: TokenTracker, mock_client: MagicMock):
        chain = _make_chain([{"id": 1}])
        mock_client.table.return_value = chain

        record = tracker.record_usage(
            user_id="user-123",
            operation="test",
            input_tokens=1_000_000,
            output_tokens=1_000_000,
        )

        expected_input = 2.00 * 4200
        expected_output = 12.00 * 4200
        assert record.input_cost_cop == pytest.approx(expected_input)
        assert record.output_cost_cop == pytest.approx(expected_output)
        assert record.total_cost_cop == pytest.approx(expected_input + expected_output)

    def test_record_usage_with_cv_id(self, tracker: TokenTracker, mock_client: MagicMock):
        chain = _make_chain([{"id": 1}])
        mock_client.table.return_value = chain

        record = tracker.record_usage(
            user_id="user-123",
            operation="yaml_generation",
            input_tokens=100,
            output_tokens=200,
            cv_id=42,
        )

        assert record.cv_id == 42
        inserted = chain.insert.call_args[0][0]
        assert inserted["cv_id"] == 42

    def test_record_usage_without_cv_id(self, tracker: TokenTracker, mock_client: MagicMock):
        chain = _make_chain([{"id": 1}])
        mock_client.table.return_value = chain

        record = tracker.record_usage(
            user_id="user-123",
            operation="test",
            input_tokens=100,
            output_tokens=200,
        )

        assert record.cv_id is None
        inserted = chain.insert.call_args[0][0]
        assert "cv_id" not in inserted

    def test_record_usage_db_error(self, tracker: TokenTracker, mock_client: MagicMock):
        """record_usage retorna TokenRecord incluso si la DB falla."""
        chain = _make_chain()
        chain.execute.side_effect = Exception("DB error")
        mock_client.table.return_value = chain

        record = tracker.record_usage(
            user_id="user-123",
            operation="test",
            input_tokens=100,
            output_tokens=200,
        )

        # Retorna el record aunque no se haya guardado en DB
        assert isinstance(record, TokenRecord)
        assert record.total_cost_cop > 0


# ------------------------------------------------------------------
# Tests: get_user_total_cost
# ------------------------------------------------------------------


class TestGetUserTotalCost:
    def test_total_cost_multiple_records(self, tracker: TokenTracker, mock_client: MagicMock):
        chain = _make_chain(
            [
                {"total_cost_cop": "10.5000"},
                {"total_cost_cop": "25.3000"},
                {"total_cost_cop": "5.0000"},
            ]
        )
        mock_client.table.return_value = chain

        total = tracker.get_user_total_cost("user-123")

        assert total == pytest.approx(40.8)
        chain.eq.assert_called_with("user_id", "user-123")

    def test_total_cost_no_records(self, tracker: TokenTracker, mock_client: MagicMock):
        chain = _make_chain([])
        mock_client.table.return_value = chain

        total = tracker.get_user_total_cost("user-123")

        assert total == 0.0

    def test_total_cost_db_error(self, tracker: TokenTracker, mock_client: MagicMock):
        chain = _make_chain()
        chain.execute.side_effect = Exception("DB error")
        mock_client.table.return_value = chain

        total = tracker.get_user_total_cost("user-123")

        assert total == 0.0


# ------------------------------------------------------------------
# Tests: get_user_remaining
# ------------------------------------------------------------------


class TestGetUserRemaining:
    def test_remaining_full(self, tracker: TokenTracker, mock_client: MagicMock):
        chain = _make_chain([])
        mock_client.table.return_value = chain

        remaining = tracker.get_user_remaining("user-123")

        assert remaining == USER_LIMIT_COP

    def test_remaining_partial(self, tracker: TokenTracker, mock_client: MagicMock):
        chain = _make_chain([{"total_cost_cop": "500.0000"}])
        mock_client.table.return_value = chain

        remaining = tracker.get_user_remaining("user-123")

        assert remaining == pytest.approx(1000.0)

    def test_remaining_exceeded(self, tracker: TokenTracker, mock_client: MagicMock):
        chain = _make_chain([{"total_cost_cop": "2000.0000"}])
        mock_client.table.return_value = chain

        remaining = tracker.get_user_remaining("user-123")

        assert remaining == 0.0


# ------------------------------------------------------------------
# Tests: is_user_blocked
# ------------------------------------------------------------------


class TestIsUserBlocked:
    def test_not_blocked(self, tracker: TokenTracker, mock_client: MagicMock):
        chain = _make_chain([{"total_cost_cop": "100.0000"}])
        mock_client.table.return_value = chain

        assert tracker.is_user_blocked("user-123") is False

    def test_blocked_exact_limit(self, tracker: TokenTracker, mock_client: MagicMock):
        chain = _make_chain([{"total_cost_cop": "1500.0000"}])
        mock_client.table.return_value = chain

        assert tracker.is_user_blocked("user-123") is True

    def test_blocked_exceeded(self, tracker: TokenTracker, mock_client: MagicMock):
        chain = _make_chain([{"total_cost_cop": "2000.0000"}])
        mock_client.table.return_value = chain

        assert tracker.is_user_blocked("user-123") is True

    def test_not_blocked_no_usage(self, tracker: TokenTracker, mock_client: MagicMock):
        chain = _make_chain([])
        mock_client.table.return_value = chain

        assert tracker.is_user_blocked("user-123") is False


# ------------------------------------------------------------------
# Tests: reset_user_tokens
# ------------------------------------------------------------------


class TestResetUserTokens:
    def test_reset_with_data(self, tracker: TokenTracker, mock_client: MagicMock):
        chain = _make_chain([{"id": 1}, {"id": 2}, {"id": 3}])
        mock_client.table.return_value = chain

        count = tracker.reset_user_tokens("user-123")

        assert count == 3
        mock_client.table.assert_called_with("token_usage")
        chain.delete.assert_called_once()
        chain.eq.assert_called_with("user_id", "user-123")

    def test_reset_no_data(self, tracker: TokenTracker, mock_client: MagicMock):
        chain = _make_chain([])
        mock_client.table.return_value = chain

        count = tracker.reset_user_tokens("user-123")

        assert count == 0

    def test_reset_db_error(self, tracker: TokenTracker, mock_client: MagicMock):
        chain = _make_chain()
        chain.execute.side_effect = Exception("DB error")
        mock_client.table.return_value = chain

        count = tracker.reset_user_tokens("user-123")

        assert count == 0


# ------------------------------------------------------------------
# Tests: get_usage_history
# ------------------------------------------------------------------


class TestGetUsageHistory:
    def test_history_returns_records(self, tracker: TokenTracker, mock_client: MagicMock):
        chain = _make_chain(
            [
                {
                    "operation": "gap_analysis",
                    "input_tokens": 1000,
                    "output_tokens": 500,
                    "input_cost_cop": "0.0084",
                    "output_cost_cop": "0.0252",
                    "total_cost_cop": "0.0336",
                    "model_used": "gemini-3-flash-preview",
                    "created_at": "2026-01-01T00:00:00+00:00",
                    "cv_id": 1,
                },
            ]
        )
        mock_client.table.return_value = chain

        records = tracker.get_usage_history("user-123", limit=10)

        assert len(records) == 1
        assert isinstance(records[0], TokenRecord)
        assert records[0].operation == "gap_analysis"
        chain.limit.assert_called_with(10)

    def test_history_empty(self, tracker: TokenTracker, mock_client: MagicMock):
        chain = _make_chain([])
        mock_client.table.return_value = chain

        records = tracker.get_usage_history("user-123")

        assert records == []


# ------------------------------------------------------------------
# Tests: get_usage_summary_by_cv
# ------------------------------------------------------------------


class TestGetUsageSummaryByCv:
    def test_summary_groups_by_cv(self, tracker: TokenTracker, mock_client: MagicMock):
        chain = _make_chain()
        mock_client.table.return_value = chain
        chain.execute.side_effect = [
            # Primera query: token_usage
            MockResponse(
                [
                    {
                        "cv_id": 1,
                        "input_tokens": 100,
                        "output_tokens": 50,
                        "total_cost_cop": "10.0000",
                        "created_at": "2026-01-01",
                    },
                    {
                        "cv_id": 1,
                        "input_tokens": 200,
                        "output_tokens": 100,
                        "total_cost_cop": "20.0000",
                        "created_at": "2026-01-02",
                    },
                    {
                        "cv_id": 2,
                        "input_tokens": 50,
                        "output_tokens": 25,
                        "total_cost_cop": "5.0000",
                        "created_at": "2026-01-03",
                    },
                ]
            ),
            # Segunda query: cv_history (titulos)
            MockResponse(
                [
                    {"id": 1, "job_title": "Python Dev"},
                    {"id": 2, "job_title": "Data Engineer"},
                ]
            ),
        ]

        summaries = tracker.get_usage_summary_by_cv("user-123")

        assert len(summaries) == 2
        # CV 1
        cv1 = next(s for s in summaries if s.cv_id == 1)
        assert cv1.total_input_tokens == 300
        assert cv1.total_output_tokens == 150
        assert cv1.total_cost_cop == pytest.approx(30.0)
        assert cv1.operations_count == 2
        assert cv1.job_title == "Python Dev"

    def test_summary_empty(self, tracker: TokenTracker, mock_client: MagicMock):
        chain = _make_chain([])
        mock_client.table.return_value = chain

        summaries = tracker.get_usage_summary_by_cv("user-123")

        assert summaries == []


# ------------------------------------------------------------------
# Tests: log_audit_action
# ------------------------------------------------------------------


class TestLogAuditAction:
    def test_log_activate(self, tracker: TokenTracker, mock_client: MagicMock):
        chain = _make_chain([{"id": 1}])
        mock_client.table.return_value = chain

        tracker.log_audit_action(
            user_id="user-123",
            admin_id="admin-456",
            action="activate",
            tokens_at_action=5000,
            cost_at_action_cop=100.50,
            notes="Reactivado por solicitud",
        )

        mock_client.table.assert_called_with("user_audit_log")
        inserted = chain.insert.call_args[0][0]
        assert inserted["user_id"] == "user-123"
        assert inserted["admin_id"] == "admin-456"
        assert inserted["action"] == "activate"
        assert inserted["tokens_at_action"] == 5000
        assert inserted["notes"] == "Reactivado por solicitud"

    def test_log_deactivate(self, tracker: TokenTracker, mock_client: MagicMock):
        chain = _make_chain([{"id": 1}])
        mock_client.table.return_value = chain

        tracker.log_audit_action(
            user_id="user-123",
            admin_id="admin-456",
            action="deactivate",
        )

        inserted = chain.insert.call_args[0][0]
        assert inserted["action"] == "deactivate"
        assert "notes" not in inserted


# ------------------------------------------------------------------
# Tests: get_audit_log
# ------------------------------------------------------------------


class TestGetAuditLog:
    def test_get_all(self, tracker: TokenTracker, mock_client: MagicMock):
        chain = _make_chain(
            [
                {"user_id": "u1", "action": "activate", "created_at": "2026-01-01"},
                {"user_id": "u2", "action": "deactivate", "created_at": "2026-01-02"},
            ]
        )
        mock_client.table.return_value = chain

        logs = tracker.get_audit_log()

        assert len(logs) == 2
        mock_client.table.assert_called_with("user_audit_log")

    def test_filter_by_user(self, tracker: TokenTracker, mock_client: MagicMock):
        chain = _make_chain([])
        mock_client.table.return_value = chain

        tracker.get_audit_log(user_id="user-123")

        chain.eq.assert_any_call("user_id", "user-123")

    def test_filter_by_action(self, tracker: TokenTracker, mock_client: MagicMock):
        chain = _make_chain([])
        mock_client.table.return_value = chain

        tracker.get_audit_log(action_filter="activate")

        chain.eq.assert_any_call("action", "activate")


# ------------------------------------------------------------------
# Tests: TokenRecord dataclass
# ------------------------------------------------------------------


class TestTokenRecord:
    def test_defaults(self):
        record = TokenRecord(
            operation="test",
            input_tokens=0,
            output_tokens=0,
            input_cost_cop=0.0,
            output_cost_cop=0.0,
            total_cost_cop=0.0,
            model_used="test",
        )
        assert record.created_at is None
        assert record.cv_id is None

    def test_with_all_fields(self):
        record = TokenRecord(
            operation="gap_analysis",
            input_tokens=1000,
            output_tokens=500,
            input_cost_cop=0.0084,
            output_cost_cop=0.0252,
            total_cost_cop=0.0336,
            model_used="gemini-3-flash-preview",
            created_at="2026-01-01",
            cv_id=42,
        )
        assert record.cv_id == 42
        assert record.created_at == "2026-01-01"


# ------------------------------------------------------------------
# Tests: CVUsageSummary dataclass
# ------------------------------------------------------------------


class TestCVUsageSummary:
    def test_summary(self):
        summary = CVUsageSummary(
            cv_id=1,
            job_title="Python Developer",
            total_input_tokens=5000,
            total_output_tokens=2000,
            total_cost_cop=150.50,
            operations_count=10,
            last_used="2026-01-01",
        )
        assert summary.cv_id == 1
        assert summary.job_title == "Python Developer"
        assert summary.operations_count == 10
