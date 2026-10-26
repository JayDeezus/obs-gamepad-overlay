"""
Reads an XInput controller (e.g. Logitech F310 in X mode) and broadcasts
button state to any connected WebSocket client (your OBS overlay page).

Setup (Windows):
    pip install XInput-Python websockets
Run:
    python gamepad_server.py
"""
import asyncio
import json

import websockets
import XInput

PORT = 8765
POLL_HZ = 120
TRIGGER_THRESHOLD = 0.3   # 0.0-1.0, how far a trigger must be pulled to count
CONTROLLER_INDEX = 0      # 0-3, first connected XInput controller

clients = set()


def read_state():
    """Return {element_id: bool} matching the ids in controller.htm, or None."""
    try:
        state = XInput.get_state(CONTROLLER_INDEX)
    except XInput.XInputNotConnectedError:
        return None

    b = XInput.get_button_values(state)
    lt, rt = XInput.get_trigger_values(state)

    return {
        "button0": b["A"],
        "button1": b["B"],
        "button2": b["X"],
        "button3": b["Y"],
        "button4": b["LEFT_SHOULDER"],
        "button5": b["RIGHT_SHOULDER"],
        "button6": lt > TRIGGER_THRESHOLD,
        "button7": rt > TRIGGER_THRESHOLD,
        "buttonC": b["DPAD_UP"],
        "buttonD": b["DPAD_DOWN"],
        "buttonE": b["DPAD_LEFT"],
        "buttonF": b["DPAD_RIGHT"],
    }


last_sent = None


async def handler(ws):
    clients.add(ws)
    try:
        # Send current state immediately so a freshly loaded page is correct
        if last_sent is not None:
            await ws.send(last_sent)
        await ws.wait_closed()
    finally:
        clients.discard(ws)


async def poll_loop():
    global last_sent
    while True:
        state = read_state()
        if state is not None:
            msg = json.dumps(state)
            if msg != last_sent:          # only send on change
                last_sent = msg
                websockets.broadcast(clients, msg)
        await asyncio.sleep(1 / POLL_HZ)


async def main():
    async with websockets.serve(handler, "localhost", PORT):
        print(f"Gamepad server running on ws://localhost:{PORT}")
        await poll_loop()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Gamepad server stopped.")
