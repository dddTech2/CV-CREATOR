"""
Tests para el modulo de autenticacion (src/auth.py).

Todos los tests usan mocks del cliente Supabase.
"""

import os
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from src.auth import AuthManager, AuthResult, _translate_error

# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------


def _mock_user(
    user_id: str = "aaaa-bbbb-cccc-dddd",
    email: str = "test@example.com",
) -> SimpleNamespace:
    """Crea un mock de gotrue.User."""
    return SimpleNamespace(id=user_id, email=email)


def _mock_session(
    access_token: str = "access-token-123",
    refresh_token: str = "refresh-token-456",
) -> SimpleNamespace:
    """Crea un mock de gotrue.Session."""
    return SimpleNamespace(access_token=access_token, refresh_token=refresh_token)


# ------------------------------------------------------------------
# Fixtures
# ------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_singleton():
    """Reset singleton antes y despues de cada test."""
    AuthManager._client = None
    yield
    AuthManager._client = None


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
        patch("src.auth.create_client") as mock_create,
    ):
        client = MagicMock()
        mock_create.return_value = client
        yield client


# ------------------------------------------------------------------
# AuthResult dataclass
# ------------------------------------------------------------------


class TestAuthResult:
    def test_success_result(self):
        result = AuthResult(
            success=True,
            user={"id": "123", "email": "a@b.com"},
            session={"access_token": "tok"},
        )
        assert result.success is True
        assert result.user is not None
        assert result.user["email"] == "a@b.com"
        assert result.error is None

    def test_error_result(self):
        result = AuthResult(success=False, error="Algo salio mal")
        assert result.success is False
        assert result.user is None
        assert result.error == "Algo salio mal"

    def test_defaults(self):
        result = AuthResult(success=True)
        assert result.user is None
        assert result.error is None
        assert result.session is None


# ------------------------------------------------------------------
# _translate_error
# ------------------------------------------------------------------


class TestTranslateError:
    def test_user_already_registered(self):
        msg = _translate_error("User already registered")
        assert "ya esta registrado" in msg

    def test_invalid_login_credentials(self):
        msg = _translate_error("Invalid login credentials")
        assert "incorrectos" in msg

    def test_password_too_short(self):
        msg = _translate_error("Password should be at least 6 characters")
        assert "6 caracteres" in msg

    def test_unknown_error(self):
        msg = _translate_error("Something weird happened")
        assert "Error de autenticacion" in msg
        assert "Something weird happened" in msg

    def test_case_insensitive(self):
        msg = _translate_error("user already REGISTERED")
        assert "ya esta registrado" in msg


# ------------------------------------------------------------------
# AuthManager.__init__
# ------------------------------------------------------------------


class TestAuthManagerInit:
    def test_init_creates_client(self, mock_client: MagicMock):
        manager = AuthManager()
        assert manager.client is mock_client

    def test_init_missing_env_vars(self):
        with (
            patch.dict(os.environ, {}, clear=True),
            pytest.raises(  # noqa: SIM117
                ValueError, match="SUPABASE_URL"
            ),
        ):
            AuthManager()

    def test_init_singleton_reuses_client(self, mock_client: MagicMock):
        m1 = AuthManager()
        m2 = AuthManager()
        assert m1.client is m2.client


# ------------------------------------------------------------------
# sign_up
# ------------------------------------------------------------------


class TestSignUp:
    def test_signup_success(self, mock_client: MagicMock):
        user = _mock_user()
        session = _mock_session()
        mock_client.auth.sign_up.return_value = SimpleNamespace(user=user, session=session)

        manager = AuthManager()
        result = manager.sign_up("test@example.com", "password123")

        assert result.success is True
        assert result.user is not None
        assert result.user["email"] == "test@example.com"
        assert result.session is not None
        assert result.session["access_token"] == "access-token-123"
        mock_client.auth.sign_up.assert_called_once_with(
            {"email": "test@example.com", "password": "password123"}
        )

    def test_signup_no_user_returned(self, mock_client: MagicMock):
        mock_client.auth.sign_up.return_value = SimpleNamespace(user=None, session=None)

        manager = AuthManager()
        result = manager.sign_up("test@example.com", "pw")

        assert result.success is False
        assert "No se pudo crear" in (result.error or "")

    def test_signup_email_duplicate(self, mock_client: MagicMock):
        mock_client.auth.sign_up.side_effect = Exception("User already registered")

        manager = AuthManager()
        result = manager.sign_up("dup@example.com", "password123")

        assert result.success is False
        assert "ya esta registrado" in (result.error or "")

    def test_signup_weak_password(self, mock_client: MagicMock):
        mock_client.auth.sign_up.side_effect = Exception("Password should be at least 6 characters")

        manager = AuthManager()
        result = manager.sign_up("test@example.com", "12")

        assert result.success is False
        assert "6 caracteres" in (result.error or "")

    def test_signup_without_session(self, mock_client: MagicMock):
        """Signup puede no devolver sesion (email confirmation requerido)."""
        user = _mock_user()
        mock_client.auth.sign_up.return_value = SimpleNamespace(user=user, session=None)

        manager = AuthManager()
        result = manager.sign_up("test@example.com", "password123")

        assert result.success is True
        assert result.session is None


# ------------------------------------------------------------------
# sign_in
# ------------------------------------------------------------------


class TestSignIn:
    def test_signin_success(self, mock_client: MagicMock):
        user = _mock_user()
        session = _mock_session()
        mock_client.auth.sign_in_with_password.return_value = SimpleNamespace(
            user=user, session=session
        )

        manager = AuthManager()
        result = manager.sign_in("test@example.com", "password123")

        assert result.success is True
        assert result.user is not None
        assert result.user["id"] == "aaaa-bbbb-cccc-dddd"
        assert result.session is not None
        mock_client.auth.sign_in_with_password.assert_called_once_with(
            {"email": "test@example.com", "password": "password123"}
        )

    def test_signin_invalid_credentials(self, mock_client: MagicMock):
        mock_client.auth.sign_in_with_password.side_effect = Exception("Invalid login credentials")

        manager = AuthManager()
        result = manager.sign_in("test@example.com", "wrong")

        assert result.success is False
        assert "incorrectos" in (result.error or "")

    def test_signin_no_user_returned(self, mock_client: MagicMock):
        mock_client.auth.sign_in_with_password.return_value = SimpleNamespace(
            user=None, session=None
        )

        manager = AuthManager()
        result = manager.sign_in("test@example.com", "password123")

        assert result.success is False
        assert "invalidas" in (result.error or "").lower()

    def test_signin_without_session(self, mock_client: MagicMock):
        user = _mock_user()
        mock_client.auth.sign_in_with_password.return_value = SimpleNamespace(
            user=user, session=None
        )

        manager = AuthManager()
        result = manager.sign_in("test@example.com", "password123")

        assert result.success is True
        assert result.session is None


# ------------------------------------------------------------------
# sign_out
# ------------------------------------------------------------------


class TestSignOut:
    def test_signout_success(self, mock_client: MagicMock):
        manager = AuthManager()
        result = manager.sign_out()

        assert result is True
        mock_client.auth.sign_out.assert_called_once()

    def test_signout_error(self, mock_client: MagicMock):
        mock_client.auth.sign_out.side_effect = Exception("Network error")

        manager = AuthManager()
        result = manager.sign_out()

        assert result is False


# ------------------------------------------------------------------
# get_current_user / get_user_id
# ------------------------------------------------------------------


class TestGetCurrentUser:
    def test_with_active_session(self, mock_client: MagicMock):
        user = _mock_user(user_id="uid-123", email="active@test.com")
        mock_client.auth.get_user.return_value = SimpleNamespace(user=user)

        manager = AuthManager()
        result = manager.get_current_user()

        assert result is not None
        assert result["id"] == "uid-123"
        assert result["email"] == "active@test.com"

    def test_without_session(self, mock_client: MagicMock):
        mock_client.auth.get_user.return_value = None

        manager = AuthManager()
        result = manager.get_current_user()

        assert result is None

    def test_with_exception(self, mock_client: MagicMock):
        mock_client.auth.get_user.side_effect = Exception("expired")

        manager = AuthManager()
        result = manager.get_current_user()

        assert result is None

    def test_get_user_id_with_session(self, mock_client: MagicMock):
        user = _mock_user(user_id="uid-456")
        mock_client.auth.get_user.return_value = SimpleNamespace(user=user)

        manager = AuthManager()
        uid = manager.get_user_id()

        assert uid == "uid-456"

    def test_get_user_id_without_session(self, mock_client: MagicMock):
        mock_client.auth.get_user.return_value = None

        manager = AuthManager()
        uid = manager.get_user_id()

        assert uid is None


# ------------------------------------------------------------------
# is_admin
# ------------------------------------------------------------------


class TestIsAdmin:
    def _setup_profile_query(self, mock_client: MagicMock, data: list[dict]) -> MagicMock:
        chain = MagicMock()
        mock_client.table.return_value = chain
        chain.select.return_value = chain
        chain.eq.return_value = chain
        chain.execute.return_value = SimpleNamespace(data=data)
        return chain

    def test_admin_user(self, mock_client: MagicMock):
        self._setup_profile_query(mock_client, [{"role": "admin"}])

        manager = AuthManager()
        assert manager.is_admin("uid-123") is True

    def test_regular_user(self, mock_client: MagicMock):
        self._setup_profile_query(mock_client, [{"role": "user"}])

        manager = AuthManager()
        assert manager.is_admin("uid-123") is False

    def test_user_not_found(self, mock_client: MagicMock):
        self._setup_profile_query(mock_client, [])

        manager = AuthManager()
        assert manager.is_admin("uid-123") is False

    def test_query_error(self, mock_client: MagicMock):
        mock_client.table.side_effect = Exception("DB error")

        manager = AuthManager()
        assert manager.is_admin("uid-123") is False


# ------------------------------------------------------------------
# is_user_active
# ------------------------------------------------------------------


class TestIsUserActive:
    def _setup_profile_query(self, mock_client: MagicMock, data: list[dict]) -> MagicMock:
        chain = MagicMock()
        mock_client.table.return_value = chain
        chain.select.return_value = chain
        chain.eq.return_value = chain
        chain.execute.return_value = SimpleNamespace(data=data)
        return chain

    def test_active_user(self, mock_client: MagicMock):
        self._setup_profile_query(mock_client, [{"is_active": True}])

        manager = AuthManager()
        assert manager.is_user_active("uid-123") is True

    def test_inactive_user(self, mock_client: MagicMock):
        self._setup_profile_query(mock_client, [{"is_active": False}])

        manager = AuthManager()
        assert manager.is_user_active("uid-123") is False

    def test_no_profile_defaults_active(self, mock_client: MagicMock):
        self._setup_profile_query(mock_client, [])

        manager = AuthManager()
        assert manager.is_user_active("uid-123") is True

    def test_query_error_defaults_active(self, mock_client: MagicMock):
        mock_client.table.side_effect = Exception("DB error")

        manager = AuthManager()
        assert manager.is_user_active("uid-123") is True


# ------------------------------------------------------------------
# get_user_profile
# ------------------------------------------------------------------


class TestGetUserProfile:
    def _setup_profile_query(self, mock_client: MagicMock, data: list[dict]) -> MagicMock:
        chain = MagicMock()
        mock_client.table.return_value = chain
        chain.select.return_value = chain
        chain.eq.return_value = chain
        chain.execute.return_value = SimpleNamespace(data=data)
        return chain

    def test_profile_found(self, mock_client: MagicMock):
        profile = {
            "id": "uid-123",
            "email": "test@example.com",
            "display_name": "Test User",
            "role": "user",
            "is_active": True,
        }
        self._setup_profile_query(mock_client, [profile])

        manager = AuthManager()
        result = manager.get_user_profile("uid-123")

        assert result is not None
        assert result["email"] == "test@example.com"
        assert result["role"] == "user"

    def test_profile_not_found(self, mock_client: MagicMock):
        self._setup_profile_query(mock_client, [])

        manager = AuthManager()
        result = manager.get_user_profile("uid-123")

        assert result is None

    def test_query_error(self, mock_client: MagicMock):
        mock_client.table.side_effect = Exception("DB error")

        manager = AuthManager()
        result = manager.get_user_profile("uid-123")

        assert result is None
