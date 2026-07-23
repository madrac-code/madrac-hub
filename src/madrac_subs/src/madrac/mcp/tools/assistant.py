"""Assistant action MCP tools."""
from __future__ import annotations
from typing import Any


def execute_assistant_action(app_state: dict[str, Any]):
    async def _execute_assistant_action(
        accion: str,
        parametro: str = "",
    ) -> str:
        """
        Execute a named assistant action.

        Args:
            accion: Action name (e.g. 'reproducir_musica', 'obtener_hora')
            parametro: Optional parameter for the action

        Returns:
            Result message from the action.
        """
        am = app_state.get("assistant_manager")
        if am is None:
            return "Error: assistant not running"
        try:
            result = am.execute_action(accion, parametro)
            return str(result) if result else f"Action '{accion}' executed"
        except Exception as e:
            return f"Error executing action '{accion}': {e}"
    return _execute_assistant_action
