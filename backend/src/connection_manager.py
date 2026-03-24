"""
connection_manager.py - WebSocket rooms, broadcasting, and streaming.

Manages active connections and routes messages to connected players.
"""
from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Any, AsyncIterator

from fastapi import WebSocket

from .debug_tools import log_debug, summarize_payload
from .models import WSMessageType

logger = logging.getLogger(__name__)


@dataclass
class PlayerConnection:
    player_id: str
    username: str
    websocket: WebSocket


class ConnectionManager:
    """Singleton that manages all active WebSocket connections."""

    def __init__(self) -> None:
        # player_id -> PlayerConnection
        self._connections: dict[str, PlayerConnection] = {}

    async def connect(self, websocket: WebSocket, player_id: str, username: str) -> None:
        await websocket.accept()
        self._connections[player_id] = PlayerConnection(
            player_id=player_id,
            username=username,
            websocket=websocket,
        )
        logger.info("Player %s (%s) connected. Total: %d", username, player_id, len(self._connections))

    def disconnect(self, player_id: str) -> None:
        if player_id in self._connections:
            conn = self._connections.pop(player_id)
            logger.info("Player %s disconnected. Total: %d", conn.username, len(self._connections))

    def is_connected(self, player_id: str) -> bool:
        return player_id in self._connections

    def connected_player_ids(self) -> list[str]:
        return list(self._connections.keys())

    def connected_count(self) -> int:
        return len(self._connections)

    async def send_to(self, player_id: str, message: dict[str, Any]) -> bool:
        """Send a message to one player. Returns False if disconnected."""
        conn = self._connections.get(player_id)
        if conn is None:
            return False
        try:
            await conn.websocket.send_text(json.dumps(message, ensure_ascii=False))
            log_debug(logger, "ws_send_to", player_id=player_id, message=summarize_payload(message))
            return True
        except Exception as exc:
            logger.warning("Failed to send to %s: %s", player_id, exc)
            self.disconnect(player_id)
            return False

    async def broadcast(self, message: dict[str, Any]) -> None:
        """Send a message to all connected players."""
        if not self._connections:
            return
        log_debug(
            logger,
            "ws_broadcast",
            recipients=len(self._connections),
            message=summarize_payload(message),
        )
        disconnected: list[str] = []
        tasks = [self._send_safe(pid, conn, message) for pid, conn in self._connections.items()]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for pid, result in zip(list(self._connections.keys()), results):
            if isinstance(result, Exception) or result is False:
                disconnected.append(pid)
        for pid in disconnected:
            self.disconnect(pid)

    async def _send_safe(
        self, player_id: str, conn: PlayerConnection, message: dict[str, Any]
    ) -> bool:
        try:
            await conn.websocket.send_text(json.dumps(message, ensure_ascii=False))
            return True
        except Exception as exc:
            logger.warning("Broadcast failed for %s: %s", player_id, exc)
            return False

    async def broadcast_stream(self, stream: AsyncIterator[str]) -> str:
        """
        Receive an async iterator of tokens and stream them to all players.
        Returns the full narrative after streaming completes.
        """
        full_narrative = ""
        token_count = 0

        async for token in stream:
            full_narrative += token
            token_count += 1
            await self.broadcast(
                {
                    "type": WSMessageType.NARRATIVE_TOKEN,
                    "token": token,
                }
            )

        log_debug(
            logger,
            "ws_stream_complete",
            token_count=token_count,
            narrative_chars=len(full_narrative),
        )

        return full_narrative

    async def broadcast_gm_thinking(self) -> None:
        """Broadcast a 'GM is thinking...' signal to everyone."""
        await self.broadcast(
            {
                "type": WSMessageType.GM_THINKING,
                "message": "The Game Master is weighing your fate...",
            }
        )

    async def broadcast_game_event(self, event_type: str, payload: dict[str, Any]) -> None:
        """Broadcast a game event such as DEATH or LEVELUP."""
        await self.broadcast(
            {
                "type": WSMessageType.GAME_EVENT,
                "event": event_type,
                "payload": payload,
            }
        )

    async def broadcast_dice_roll(self, dice_data: dict[str, Any]) -> None:
        """Pause narrative flow and surface a dice-roll event."""
        await self.broadcast(
            {
                "type": WSMessageType.DICE_ROLL,
                **dice_data,
            }
        )

    async def broadcast_full_state_sync(self, state: dict[str, Any]) -> None:
        """Broadcast a full state sync, usually after reconnection."""
        await self.broadcast(
            {
                "type": WSMessageType.FULL_STATE_SYNC,
                "state": state,
            }
        )

    async def send_isekai_convocation(
        self, player_id: str, narrative: str, faction: str, secret_objective: str
    ) -> None:
        """Send a personalized isekai convocation narrative to one player."""
        await self.send_to(
            player_id,
            {
                "type": WSMessageType.ISEKAI_CONVOCATION,
                "narrative": narrative,
                "faction": faction,
                "secret_objective": secret_objective,
            },
        )


# Global instance imported by other modules
manager = ConnectionManager()
