import asyncio
from typing import Any

import socketio

from cluedo_assistant import cluedo_assistant
from common.io.message_io import MessageIo

# Session storage
sessions = {}

sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")
app = socketio.ASGIApp(sio)


@sio.event
async def connect(sid: str, environ) -> None:
    print(f"Client connected: {sid}")
    receive_queue = asyncio.Queue[dict[str, Any]]()
    message_io = MessageIo(sio=sio, sid=sid, receive_queue=receive_queue)
    sessions[sid] = {
        "receive_queue": receive_queue,
        "task": None,
    }

    task = asyncio.create_task(run_assistant(sid, message_io))
    sessions[sid]["task"] = task


@sio.event
async def disconnect(sid):
    print(f"Client disconnected: {sid}")
    if sid in sessions:
        task = sessions[sid]["task"]
        if task:
            task.cancel()
        del sessions[sid]


@sio.event
async def user_input(sid, data):
    print(f"Message from {sid}: {data}")
    if sid in sessions:
        await sessions[sid]["receive_queue"].put(data)


async def run_assistant(sid: str, message_io: MessageIo) -> None:
    try:
        await cluedo_assistant(message_io)
    except Exception as e:
        print(f"Error in assistant for {sid}: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=5005)
