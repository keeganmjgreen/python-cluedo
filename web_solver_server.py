import asyncio
import queue
from typing import Any

import socketio

from cluedo_assistant import cluedo_assistant
from common.io.message_io import MessageIo

# Session storage
sessions = {}

sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")
app = socketio.ASGIApp(sio)


@sio.event
async def connect(sid, environ):
    print(f"Client connected: {sid}")
    send_queue = queue.Queue[dict[str, Any]]()
    receive_queue = queue.Queue[dict[str, Any]]()
    chat_io = MessageIo(send_queue=send_queue, receive_queue=receive_queue)
    sessions[sid] = {
        "send_queue": send_queue,
        "receive_queue": receive_queue,
        "task": None,
        "send_task": None,
    }

    # Start the assistant in a thread
    task = asyncio.create_task(run_assistant(sid, chat_io))
    sessions[sid]["task"] = task

    # Start sending messages
    send_task = asyncio.create_task(send_messages(sid))
    sessions[sid]["send_task"] = send_task


@sio.event
async def disconnect(sid):
    print(f"Client disconnected: {sid}")
    if sid in sessions:
        task = sessions[sid]["task"]
        send_task = sessions[sid]["send_task"]
        if task:
            task.cancel()
        if send_task:
            send_task.cancel()
        del sessions[sid]


@sio.event
async def user_input(sid, data):
    print(f"Message from {sid}: {data}")
    if sid in sessions:
        sessions[sid]["receive_queue"].put(data)


async def run_assistant(sid, chat_io):
    try:
        await asyncio.to_thread(cluedo_assistant, dashboard=False, io=chat_io)
    except Exception as e:
        print(f"Error in assistant for {sid}: {e}")
        import traceback

        traceback.print_exc()


async def send_messages(sid):
    loop = asyncio.get_event_loop()
    while sid in sessions:
        try:
            # Get from sync queue in a thread
            message = await loop.run_in_executor(None, sessions[sid]["send_queue"].get)
            await sio.emit("message", message, to=sid)
        except Exception as e:
            print(f"Error sending to {sid}: {e}")
            break


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=5005)
