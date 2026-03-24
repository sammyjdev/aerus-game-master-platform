"""Test WebSocket client — use it in the terminal to interact with the GM."""
import asyncio
import json
import sys

import websockets

TOKEN = sys.argv[1] if len(sys.argv) > 1 else ""
URL = f"ws://localhost:8000/ws/{TOKEN}"


async def main() -> None:
    print(f"\nConnecting to {URL[:60]}...\n")

    async with websockets.connect(URL) as ws:
        print("Connected! Waiting for state sync...\n")

        # Receive server messages in the background
        async def receive() -> None:
            async for raw in ws:
                msg = json.loads(raw)
                _render(msg)

        recv_task = asyncio.create_task(receive())

        # Action sending loop
        loop = asyncio.get_event_loop()
        while True:
            action = await loop.run_in_executor(None, lambda: input("\n> Your action: "))
            if action.lower() in ("leave", "exit", "quit"):
                break
            await ws.send(json.dumps({"action": action}))

        recv_task.cancel()


def _render(msg: dict) -> None:
    t = msg.get("type", "")

    if t == "narrative_token":
        print(msg.get("token", ""), end="", flush=True)

    elif t == "full_state_sync":
        s = msg.get("state", {})
        print(f"\n{'─'*50}")
        print(f"  {s.get('name')} | Level {s.get('level')} | HP {s.get('current_hp')}/{s.get('max_hp')}")
        print(f"{'─'*50}\n")

    elif t == "isekai_convocation":
        print(f"\n{'═'*50}")
        print("  ✦ CONVOCATION TO AERUS ✦")
        print(f"{'═'*50}")
        print(msg.get("narrative", ""))
        print(f"\n  Secret objective: {msg.get('secret_objective', '')}")
        print(f"{'═'*50}\n")

    elif t == "dice_roll":
        player = msg.get("player", "?")
        roll_type = msg.get("type", "d20")
        purpose = msg.get("purpose", "")
        result = msg.get("result", "?")
        print(f"\n  🎲 {player} rolls {roll_type} ({purpose}): {result}")

    elif t == "game_event":
        event = msg.get("event", "")
        payload = msg.get("payload", {})
        print(f"\n  ⚡ [{event}] {payload}")

    elif t == "gm_thinking":
        print(f"\n  ⏳ {msg.get('message', '')}")

    elif t == "audio_cue":
        print(f"\n  🎵 [{msg.get('cue')}]")

    elif t == "token_refresh":
        print(f"\n  🔄 Token refreshed silently")

    elif t == "error":
        print(f"\n  ❌ Error: {msg.get('message')}")

    else:
        print(f"\n  [{t}] {msg}")


if __name__ == "__main__":
    asyncio.run(main())
