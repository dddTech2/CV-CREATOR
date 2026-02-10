"""
Modulo de tracking de tokens y costos de IA.

Registra el consumo de tokens por usuario, calcula costos en COP
y controla el limite de gasto por usuario.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from src.logger import get_logger
from supabase import Client, create_client

logger = get_logger(__name__)

# ------------------------------------------------------------------
# Constantes de precios (Gemini 3 Pro Preview)
# ------------------------------------------------------------------
INPUT_PRICE_USD_PER_M: float = 2.00
OUTPUT_PRICE_USD_PER_M: float = 12.00
TRM_COP_USD: float = 4200.0
USER_LIMIT_COP: float = 1500.0


def calculate_cost_cop(input_tokens: int, output_tokens: int) -> float:
    """Calcula el costo total en COP para una cantidad de tokens.

    Formula: (input/1M * $2 + output/1M * $12) * 4200
    """
    input_cost_usd = input_tokens / 1_000_000 * INPUT_PRICE_USD_PER_M
    output_cost_usd = output_tokens / 1_000_000 * OUTPUT_PRICE_USD_PER_M
    return (input_cost_usd + output_cost_usd) * TRM_COP_USD


# ------------------------------------------------------------------
# Dataclasses
# ------------------------------------------------------------------


@dataclass
class TokenRecord:
    """Registro individual de consumo de tokens."""

    operation: str
    input_tokens: int
    output_tokens: int
    input_cost_cop: float
    output_cost_cop: float
    total_cost_cop: float
    model_used: str
    created_at: str | None = None
    cv_id: int | None = None


@dataclass
class CVUsageSummary:
    """Resumen de consumo agrupado por CV."""

    cv_id: int | None
    job_title: str
    total_input_tokens: int
    total_output_tokens: int
    total_cost_cop: float
    operations_count: int
    last_used: str | None = None


# ------------------------------------------------------------------
# TokenTracker
# ------------------------------------------------------------------


class TokenTracker:
    """Gestiona el tracking de tokens y costos por usuario.

    Usa el mismo patron singleton de cliente Supabase.
    """

    _client: Client | None = None

    def __init__(self) -> None:
        if TokenTracker._client is None:
            url = os.environ.get("SUPABASE_URL", "")
            key = os.environ.get("SUPABASE_KEY", "")
            if not url or not key:
                raise ValueError(
                    "Las variables de entorno SUPABASE_URL y SUPABASE_KEY son requeridas."
                )
            TokenTracker._client = create_client(url, key)
        self.client: Client = TokenTracker._client

    # ------------------------------------------------------------------
    # Registrar consumo
    # ------------------------------------------------------------------

    def record_usage(
        self,
        user_id: str,
        operation: str,
        input_tokens: int,
        output_tokens: int,
        cv_id: int | None = None,
        model_used: str = "gemini-3-flash-preview",
    ) -> TokenRecord:
        """Registra una operacion de consumo de tokens.

        Args:
            user_id: UUID del usuario.
            operation: Tipo de operacion (gap_analysis, question_generation, etc.).
            input_tokens: Tokens de entrada consumidos.
            output_tokens: Tokens de salida consumidos.
            cv_id: ID del CV asociado (opcional).
            model_used: Nombre del modelo utilizado.

        Returns:
            TokenRecord con los datos registrados.
        """
        input_cost = input_tokens / 1_000_000 * INPUT_PRICE_USD_PER_M * TRM_COP_USD
        output_cost = output_tokens / 1_000_000 * OUTPUT_PRICE_USD_PER_M * TRM_COP_USD
        total_cost = input_cost + output_cost

        data: dict[str, Any] = {
            "user_id": user_id,
            "operation": operation,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "input_cost_cop": round(input_cost, 4),
            "output_cost_cop": round(output_cost, 4),
            "total_cost_cop": round(total_cost, 4),
            "model_used": model_used,
        }
        if cv_id is not None:
            data["cv_id"] = cv_id

        try:
            self.client.table("token_usage").insert(data).execute()
            logger.info(
                f"Token usage registrado: user={user_id}, op={operation}, "
                f"in={input_tokens}, out={output_tokens}, cost={total_cost:.4f} COP"
            )
        except Exception as e:
            logger.error(f"Error registrando token usage: {e}")

        return TokenRecord(
            operation=operation,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            input_cost_cop=round(input_cost, 4),
            output_cost_cop=round(output_cost, 4),
            total_cost_cop=round(total_cost, 4),
            model_used=model_used,
            cv_id=cv_id,
        )

    # ------------------------------------------------------------------
    # Consultas de consumo
    # ------------------------------------------------------------------

    def get_user_total_cost(self, user_id: str) -> float:
        """Retorna el costo acumulado en COP del usuario."""
        try:
            response = (
                self.client.table("token_usage")
                .select("total_cost_cop")
                .eq("user_id", user_id)
                .execute()
            )
            return sum(float(r["total_cost_cop"]) for r in response.data)
        except Exception as e:
            logger.error(f"Error obteniendo costo total: {e}")
            return 0.0

    def get_user_remaining(self, user_id: str) -> float:
        """Retorna los COP restantes del limite del usuario."""
        return max(0.0, USER_LIMIT_COP - self.get_user_total_cost(user_id))

    def is_user_blocked(self, user_id: str) -> bool:
        """Retorna True si el usuario excedio el limite de gasto."""
        return self.get_user_total_cost(user_id) >= USER_LIMIT_COP

    def get_usage_by_cv(self, user_id: str, cv_id: int) -> list[TokenRecord]:
        """Retorna detalle de consumo para un CV especifico."""
        try:
            response = (
                self.client.table("token_usage")
                .select("*")
                .eq("user_id", user_id)
                .eq("cv_id", cv_id)
                .order("created_at", desc=True)
                .execute()
            )
            return [self._row_to_record(r) for r in response.data]
        except Exception as e:
            logger.error(f"Error obteniendo uso por CV: {e}")
            return []

    def get_usage_summary_by_cv(self, user_id: str) -> list[CVUsageSummary]:
        """Retorna resumen de consumo agrupado por CV.

        Hace un JOIN con cv_history para obtener el job_title.
        """
        try:
            response = (
                self.client.table("token_usage")
                .select("cv_id, input_tokens, output_tokens, total_cost_cop, created_at")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .execute()
            )

            # Agrupar manualmente por cv_id
            groups: dict[int | None, dict[str, Any]] = {}
            for row in response.data:
                cv_id = row.get("cv_id")
                if cv_id not in groups:
                    groups[cv_id] = {
                        "total_input": 0,
                        "total_output": 0,
                        "total_cost": 0.0,
                        "count": 0,
                        "last_used": row.get("created_at"),
                    }
                g = groups[cv_id]
                g["total_input"] += row["input_tokens"]
                g["total_output"] += row["output_tokens"]
                g["total_cost"] += float(row["total_cost_cop"])
                g["count"] += 1

            # Obtener titulos de CVs
            cv_ids = [cid for cid in groups if cid is not None]
            titles: dict[int, str] = {}
            if cv_ids:
                try:
                    cv_response = self.client.table("cv_history").select("id, job_title").execute()
                    titles = {r["id"]: r["job_title"] for r in cv_response.data}
                except Exception:
                    pass

            summaries = []
            for cv_id, g in groups.items():
                summaries.append(
                    CVUsageSummary(
                        cv_id=cv_id,
                        job_title=titles.get(cv_id, "Sin CV asociado")
                        if cv_id
                        else "Sin CV asociado",
                        total_input_tokens=g["total_input"],
                        total_output_tokens=g["total_output"],
                        total_cost_cop=round(g["total_cost"], 4),
                        operations_count=g["count"],
                        last_used=g["last_used"],
                    )
                )
            return summaries
        except Exception as e:
            logger.error(f"Error obteniendo resumen por CV: {e}")
            return []

    def get_usage_history(self, user_id: str, limit: int = 50) -> list[TokenRecord]:
        """Retorna historial detallado de operaciones."""
        try:
            response = (
                self.client.table("token_usage")
                .select("*")
                .eq("user_id", user_id)
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )
            return [self._row_to_record(r) for r in response.data]
        except Exception as e:
            logger.error(f"Error obteniendo historial: {e}")
            return []

    def reset_user_tokens(self, user_id: str) -> int:
        """Elimina registros de token_usage para el usuario (al reactivar).

        NO borra cv_history, skill_memory, base_cv ni interview_sessions.

        Returns:
            Numero de registros eliminados.
        """
        try:
            response = self.client.table("token_usage").delete().eq("user_id", user_id).execute()
            count = len(response.data)
            logger.info(f"Reset tokens para user={user_id}: {count} registros eliminados")
            return count
        except Exception as e:
            logger.error(f"Error reseteando tokens: {e}")
            return 0

    # ------------------------------------------------------------------
    # Auditoria
    # ------------------------------------------------------------------

    def log_audit_action(
        self,
        user_id: str,
        admin_id: str,
        action: str,
        tokens_at_action: int = 0,
        cost_at_action_cop: float = 0.0,
        notes: str | None = None,
    ) -> None:
        """Registra una accion de auditoria (activar/desactivar usuario)."""
        data: dict[str, Any] = {
            "user_id": user_id,
            "admin_id": admin_id,
            "action": action,
            "tokens_at_action": tokens_at_action,
            "cost_at_action_cop": round(cost_at_action_cop, 4),
        }
        if notes:
            data["notes"] = notes

        try:
            self.client.table("user_audit_log").insert(data).execute()
            logger.info(f"Audit log: admin={admin_id} {action} user={user_id}")
        except Exception as e:
            logger.error(f"Error registrando audit log: {e}")

    def get_audit_log(
        self,
        user_id: str | None = None,
        action_filter: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        """Retorna el log de auditoria con filtros opcionales."""
        try:
            query = (
                self.client.table("user_audit_log")
                .select("*")
                .order("created_at", desc=True)
                .limit(limit)
            )
            if user_id:
                query = query.eq("user_id", user_id)
            if action_filter and action_filter in ("activate", "deactivate"):
                query = query.eq("action", action_filter)

            response = query.execute()
            return response.data  # type: ignore[return-value]
        except Exception as e:
            logger.error(f"Error obteniendo audit log: {e}")
            return []

    # ------------------------------------------------------------------
    # Admin: metricas globales
    # ------------------------------------------------------------------

    def get_all_users_usage(self) -> list[dict[str, Any]]:
        """Retorna consumo total agrupado por usuario (para admin)."""
        try:
            response = (
                self.client.table("token_usage")
                .select("user_id, input_tokens, output_tokens, total_cost_cop")
                .execute()
            )

            users: dict[str, dict[str, Any]] = {}
            for row in response.data:
                uid = row["user_id"]
                if uid not in users:
                    users[uid] = {"total_input": 0, "total_output": 0, "total_cost": 0.0}
                users[uid]["total_input"] += row["input_tokens"]
                users[uid]["total_output"] += row["output_tokens"]
                users[uid]["total_cost"] += float(row["total_cost_cop"])

            return [
                {
                    "user_id": uid,
                    "total_input_tokens": data["total_input"],
                    "total_output_tokens": data["total_output"],
                    "total_cost_cop": round(data["total_cost"], 4),
                }
                for uid, data in users.items()
            ]
        except Exception as e:
            logger.error(f"Error obteniendo uso global: {e}")
            return []

    # ------------------------------------------------------------------
    # Helpers internos
    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_record(row: dict[str, Any]) -> TokenRecord:
        """Convierte una fila de la DB a TokenRecord."""
        return TokenRecord(
            operation=row["operation"],
            input_tokens=row["input_tokens"],
            output_tokens=row["output_tokens"],
            input_cost_cop=float(row["input_cost_cop"]),
            output_cost_cop=float(row["output_cost_cop"]),
            total_cost_cop=float(row["total_cost_cop"]),
            model_used=row["model_used"],
            created_at=row.get("created_at"),
            cv_id=row.get("cv_id"),
        )
