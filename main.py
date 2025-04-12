from fastapi import FastAPI, WebSocket, Request
from fastapi.responses import HTMLResponse
import uuid
from group_chat import AutogenChat
import asyncio
import uvicorn
from dotenv import load_dotenv, find_dotenv
import os

from api.user_auth import router as user_auth_router
from api.bank_agents import router as agent_router
from database.db import Base, engine
from api.prompt_crud import router as prompt_router
from api.transactions_crud import router as transaction_router

_ = load_dotenv(find_dotenv()) # read local .env file

app = FastAPI()
app.autogen_chat = {}


class ConnectionManager:
    def __init__(self):
        self.active_connections: list[AutogenChat] = []

    async def connect(self, autogen_chat: AutogenChat):
        await autogen_chat.websocket.accept()
        self.active_connections.append(autogen_chat)

    async def disconnect(self, autogen_chat: AutogenChat):
        autogen_chat.client_receive_queue.put_nowait("DO_FINISH")
        print(f"autogen_chat {autogen_chat.chat_id} disconnected")
        self.active_connections.remove(autogen_chat)


manager = ConnectionManager()


async def send_to_client(autogen_chat: AutogenChat):
    while True:
        reply = await autogen_chat.client_receive_queue.get()
        if reply and reply == "DO_FINISH":
            autogen_chat.client_receive_queue.task_done()
            break
        await autogen_chat.websocket.send_text(reply)
        autogen_chat.client_receive_queue.task_done()
        await asyncio.sleep(0.05)

async def receive_from_client(autogen_chat: AutogenChat):
    while True:
        data = await autogen_chat.websocket.receive_text()
        if data and data == "DO_FINISH":
            await autogen_chat.client_receive_queue.put("DO_FINISH")
            await autogen_chat.client_sent_queue.put("DO_FINISH")
            break
        await autogen_chat.client_sent_queue.put(data)
        await asyncio.sleep(0.05)

@app.websocket("/api/ws/{ws_client_id}")
async def websocket_endpoint(websocket: WebSocket, ws_client_id: str):
    try:
        autogen_chat = AutogenChat(chat_id=ws_client_id, websocket=websocket)
        await manager.connect(autogen_chat)
        data = await autogen_chat.websocket.receive_text()
        future_calls = asyncio.gather(send_to_client(autogen_chat), receive_from_client(autogen_chat))
        await autogen_chat.start(data)
        print("DO_FINISHED")
    except Exception as e:
        print("ERROR", str(e))
    finally:
        try:
            await manager.disconnect(autogen_chat)
        except:
            pass

# Create the tables based on the SQLAlchemy models
Base.metadata.create_all(bind=engine)

app.include_router(user_auth_router, prefix='/api')
app.include_router(agent_router, prefix='/api')
app.include_router(prompt_router, prefix='/api')
app.include_router(transaction_router, prefix='/api')

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)