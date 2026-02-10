"""
Modulo de autenticacion con Supabase Auth para CV-App.

Encapsula las operaciones de registro, login, logout y gestion de sesion.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any

from src.logger import get_logger
from supabase import Client, create_client

logger = get_logger(__name__)


@dataclass
class AuthResult:
    """Resultado de una operacion de autenticacion."""

    success: bool
    user: dict[str, Any] | None = None
    error: str | None = None
    session: dict[str, Any] | None = field(default=None, repr=False)


# Mapeo de errores comunes de Supabase Auth a mensajes en espanol.
_ERROR_MESSAGES: dict[str, str] = {
    "User already registered": "Este email ya esta registrado.",
    "Invalid login credentials": "Email o contrasena incorrectos.",
    "Email not confirmed": "Debes confirmar tu email antes de iniciar sesion.",
    "Password should be at least 6 characters": ("La contrasena debe tener al menos 6 caracteres."),
    "Signup requires a valid password": "Debes proporcionar una contrasena valida.",
    "Unable to validate email address: invalid format": ("El formato del email no es valido."),
}


def _translate_error(error_message: str) -> str:
    """Traduce errores de Supabase Auth al espanol."""
    for key, translation in _ERROR_MESSAGES.items():
        if key.lower() in error_message.lower():
            return translation
    return f"Error de autenticacion: {error_message}"


class AuthManager:
    """Gestiona la autenticacion de usuarios via Supabase Auth.

    Usa el mismo patron singleton para el cliente Supabase que CVDatabase.
    """

    _client: Client | None = None

    def __init__(self) -> None:
        if AuthManager._client is None:
            url = os.environ.get("SUPABASE_URL", "")
            key = os.environ.get("SUPABASE_KEY", "")
            if not url or not key:
                raise ValueError(
                    "Las variables de entorno SUPABASE_URL y SUPABASE_KEY son requeridas."
                )
            AuthManager._client = create_client(url, key)
            logger.info("AuthManager: cliente Supabase inicializado")
        self.client: Client = AuthManager._client

    # ------------------------------------------------------------------
    # Registro
    # ------------------------------------------------------------------

    def sign_up(self, email: str, password: str) -> AuthResult:
        """Registra un usuario nuevo con email y contrasena.

        Args:
            email: Email del usuario.
            password: Contrasena (minimo 6 caracteres, Supabase default).

        Returns:
            AuthResult con el resultado de la operacion.
        """
        try:
            response = self.client.auth.sign_up({"email": email, "password": password})
            user = response.user
            if user is None:
                return AuthResult(success=False, error="No se pudo crear el usuario.")

            logger.info(f"Usuario registrado: {email}")
            user_dict = {
                "id": str(user.id),
                "email": user.email,
            }
            session_dict = None
            if response.session:
                session_dict = {
                    "access_token": response.session.access_token,
                    "refresh_token": response.session.refresh_token,
                }
            return AuthResult(success=True, user=user_dict, session=session_dict)
        except Exception as e:
            error_msg = str(e)
            logger.warning(f"Error en registro ({email}): {error_msg}")
            return AuthResult(success=False, error=_translate_error(error_msg))

    # ------------------------------------------------------------------
    # Login
    # ------------------------------------------------------------------

    def sign_in(self, email: str, password: str) -> AuthResult:
        """Inicia sesion con email y contrasena.

        Args:
            email: Email del usuario.
            password: Contrasena.

        Returns:
            AuthResult con la sesion si es exitoso.
        """
        try:
            response = self.client.auth.sign_in_with_password(
                {"email": email, "password": password}
            )
            user = response.user
            if user is None:
                return AuthResult(success=False, error="Credenciales invalidas.")

            logger.info(f"Login exitoso: {email}")
            user_dict = {
                "id": str(user.id),
                "email": user.email,
            }
            session_dict = None
            if response.session:
                session_dict = {
                    "access_token": response.session.access_token,
                    "refresh_token": response.session.refresh_token,
                }
            return AuthResult(success=True, user=user_dict, session=session_dict)
        except Exception as e:
            error_msg = str(e)
            logger.warning(f"Error en login ({email}): {error_msg}")
            return AuthResult(success=False, error=_translate_error(error_msg))

    # ------------------------------------------------------------------
    # Logout
    # ------------------------------------------------------------------

    def sign_out(self) -> bool:
        """Cierra la sesion del usuario actual.

        Returns:
            True si se cerro correctamente.
        """
        try:
            self.client.auth.sign_out()
            logger.info("Sesion cerrada")
            return True
        except Exception as e:
            logger.error(f"Error cerrando sesion: {e}")
            return False

    # ------------------------------------------------------------------
    # Sesion / usuario actual
    # ------------------------------------------------------------------

    def get_current_user(self) -> dict[str, Any] | None:
        """Retorna el usuario actual desde la sesion de Supabase.

        Returns:
            Diccionario con datos del usuario o None si no hay sesion.
        """
        try:
            response = self.client.auth.get_user()
            if response and response.user:
                return {
                    "id": str(response.user.id),
                    "email": response.user.email,
                }
            return None
        except Exception:
            return None

    def get_user_id(self) -> str | None:
        """Retorna el UUID del usuario actual.

        Returns:
            UUID como string o None.
        """
        user = self.get_current_user()
        return user["id"] if user else None

    # ------------------------------------------------------------------
    # Roles y perfiles
    # ------------------------------------------------------------------

    def is_admin(self, user_id: str) -> bool:
        """Verifica si un usuario tiene rol admin consultando user_profiles.

        Args:
            user_id: UUID del usuario.

        Returns:
            True si el usuario es admin.
        """
        try:
            response = self.client.table("user_profiles").select("role").eq("id", user_id).execute()
            if response.data:
                return response.data[0]["role"] == "admin"  # type: ignore[call-overload,index]
            return False
        except Exception as e:
            logger.error(f"Error verificando admin: {e}")
            return False

    def is_user_active(self, user_id: str) -> bool:
        """Verifica si un usuario esta activo consultando user_profiles.

        Args:
            user_id: UUID del usuario.

        Returns:
            True si el usuario esta activo.
        """
        try:
            response = (
                self.client.table("user_profiles").select("is_active").eq("id", user_id).execute()
            )
            if response.data:
                return bool(response.data[0]["is_active"])  # type: ignore[call-overload,index]
            # Si no hay perfil aun, asumir activo (trigger puede no haber corrido).
            return True
        except Exception as e:
            logger.error(f"Error verificando estado de usuario: {e}")
            return True

    def get_user_profile(self, user_id: str) -> dict[str, Any] | None:
        """Obtiene el perfil completo de un usuario.

        Args:
            user_id: UUID del usuario.

        Returns:
            Diccionario con datos del perfil o None.
        """
        try:
            response = self.client.table("user_profiles").select("*").eq("id", user_id).execute()
            if response.data:
                return response.data[0]  # type: ignore[return-value]
            return None
        except Exception as e:
            logger.error(f"Error obteniendo perfil: {e}")
            return None
