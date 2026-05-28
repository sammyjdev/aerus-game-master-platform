"""
connection_manager.py - WebSocket rooms, broadcasting, and streaming.

Manages active connections and routes messages to connected players.
Each connection is tagged with a ``campaign_id`` so broadcasts can be scoped
to the campaign the player belongs to. ``broadcast(msg)`` without a campaign
falls back to a global send for backwards compatibility.
"""
from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass
from typing import Any, AsyncIterator

from fastapi import WebSocket
from pydantic import TypeAdapter

from .debug_tools import log_debug, summarize_payload
from .models import WSMessageType
from .ws_contracts import OutgoingWSMessage

logger = logging.getLogger(__name__)

_outgoing_adapter: TypeAdapter[OutgoingWSMessage] = TypeAdapter(OutgoingWSMessage)


def _validate_and_serialize(message: dict[str, Any]) -> str:
    try:
        validated = _outgoing_adapter.validate_python(message)
        return json.dumps(validated.model_dump(), ensure_ascii=False)
    except Exception as exc:
        logger.error("WS contract violation: %s | message_type=%s", exc, message.get("type"))
        return json.dumps(message, ensure_ascii=False)


@dataclass
class PlayerConnection:
    player_id: str
    username: str
    websocket: WebSocket
    campaign_id: str = "default"


class ConnectionManager:
    """Singleton that manages all active WebSocket connections."""

    def __init__(self) -> None:
        # player_id -> PlayerConnection
        self._connections: dict[str, PlayerConnection] = {}

    async def connect(
        self,
        websocket: WebSocket,
        player_id: str,
        username: str,
        campaign_id: str = "default",
    ) -> None:
        await websocket.accept()
        self._connections[player_id] = PlayerConnection(
            player_id=player_id,
            username=username,
            websocket=websocket,
            campaign_id=campaign_id,
        )
        logger.info(
            "Player %s (%s) connected to campaign=%s. Total: %d",
            username, player_id, campaign_id, len(self._connections),
        )

    def disconnect(self, player_id: str) -> None:
        if player_id in self._connections:
            conn = self._connections.pop(player_id)
            logger.info("Player %s disconnected. Total: %d", conn.username, len(self._connections))

    def is_connected(self, player_id: str) -> bool:
        return player_id in self._connections

    def get_campaign(self, player_id: str) -> str | None:
        conn = self._connections.get(player_id)
        return conn.campaign_id if conn else None

    def connected_player_ids(self) -> list[str]:
        return list(self._connections.keys())

    def connected_player_ids_in_campaign(self, campaign_id: str) -> list[str]:
        return [pid for pid, c in self._connections.items() if c.campaign_id == campaign_id]

    def connected_roster_in_campaign(self, campaign_id: str) -> list[dict[str, str]]:
        return [
            {"player_id": c.player_id, "username": c.username}
            for c in self._connections.values()
            if c.campaign_id == campaign_id
        ]

    def connected_count(self) -> int:
        return len(self._connections)

    async def send_to(self, player_id: str, message: dict[str, Any]) -> bool:
        """Send a message to one player. Returns False if disconnected."""
        conn = self._connections.get(player_id)
        if conn is None:
            return False
        try:
            await conn.websocket.send_text(_validate_and_serialize(message))
            log_debug(logger, "ws_send_to", player_id=player_id, message=summarize_payload(message))
            return True
        except Exception as exc:
            logger.warning("Failed to send to %s: %s", player_id, exc)
            self.disconnect(player_id)
            return False

    def _recipients(self, campaign_id: str | None) -> list[tuple[str, PlayerConnection]]:
        if campaign_id is None:
            return list(self._connections.items())
        return [(pid, c) for pid, c in self._connections.items() if c.campaign_id == campaign_id]

    async def broadcast(
        self,
        message: dict[str, Any],
        campaign_id: str | None = None,
        exclude_player_id: str | None = None,
    ) -> None:
        """Send a message to connected players.

        If ``campaign_id`` is provided, only connections in that campaign receive it.
        ``exclude_player_id`` skips a single player (useful for player_joined/left).
        """
        recipients = self._recipients(campaign_id)
        if exclude_player_id:
            recipients = [(pid, c) for pid, c in recipients if pid != exclude_player_id]
        if not recipients:
            return
        log_debug(
            logger,
            "ws_broadcast",
            recipients=len(recipients),
            campaign_id=campaign_id,
            message=summarize_payload(message),
        )
        disconnected: list[str] = []
        tasks = [self._send_safe(pid, conn, message) for pid, conn in recipients]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        for (pid, _), result in zip(recipients, results):
            if isinstance(result, Exception) or result is False:
                disconnected.append(pid)
        for pid in disconnected:
            self.disconnect(pid)

    async def _send_safe(
        self, player_id: str, conn: PlayerConnection, message: dict[str, Any]
    ) -> bool:
        try:
            await conn.websocket.send_text(_validate_and_serialize(message))
            return True
        except Exception as exc:
            logger.warning("Broadcast failed for %s: %s", player_id, exc)
            return False

    async def broadcast_stream(
        self,
        stream: AsyncIterator[str],
        campaign_id: str | None = None,
    ) -> str:
        """
        Receive an async iterator of tokens and stream them to all players
        (optionally scoped to a campaign). Returns the full narrative.
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
                },
                campaign_id=campaign_id,
            )

        log_debug(
            logger,
            "ws_stream_complete",
            token_count=token_count,
            narrative_chars=len(full_narrative),
            campaign_id=campaign_id,
        )

        return full_narrative

    async def broadcast_gm_thinking(self, campaign_id: str | None = None) -> None:
        """Broadcast a 'GM is thinking...' signal."""
        await self.broadcast(
            {
                "type": WSMessageType.GM_THINKING,
                "message": "The Game Master is weighing your fate...",
            },
            campaign_id=campaign_id,
        )

    async def broadcast_game_event(
        self,
        event_type: str,
        payload: dict[str, Any],
        campaign_id: str | None = None,
    ) -> None:
        """Broadcast a game event such as DEATH or LEVELUP."""
        await self.broadcast(
            {
                "type": WSMessageType.GAME_EVENT,
                "event": event_type,
                "payload": payload,
            },
            campaign_id=campaign_id,
        )

    async def broadcast_dice_roll(
        self,
        dice_data: dict[str, Any],
        campaign_id: str | None = None,
    ) -> None:
        """Pause narrative flow and surface a dice-roll event."""
        await self.broadcast(
            {
                "type": WSMessageType.DICE_ROLL,
                **dice_data,
            },
            campaign_id=campaign_id,
        )

    async def broadcast_full_state_sync(
        self,
        state: dict[str, Any],
        campaign_id: str | None = None,
    ) -> None:
        """Broadcast a full state sync, usually after reconnection."""
        await self.broadcast(
            {
                "type": WSMessageType.FULL_STATE_SYNC,
                "state": state,
            },
            campaign_id=campaign_id,
        )

    async def broadcast_player_joined(
        self, campaign_id: str, player: dict[str, Any]
    ) -> None:
        """Announce that a player joined the campaign (sent to others, not the joiner)."""
        await self.broadcast(
            {
                "type": WSMessageType.PLAYER_JOINED,
                "player": player,
            },
            campaign_id=campaign_id,
            exclude_player_id=player.get("player_id"),
        )

    async def broadcast_player_left(
        self, campaign_id: str, player_id: str, username: str
    ) -> None:
        """Announce that a player left the campaign."""
        await self.broadcast(
            {
                "type": WSMessageType.PLAYER_LEFT,
                "player_id": player_id,
                "username": username,
            },
            campaign_id=campaign_id,
            exclude_player_id=player_id,
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
