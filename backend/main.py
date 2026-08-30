from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from logging_config import get_logger
from query_data import stream_graph_updates

logger = get_logger(__name__)

ICS = FastAPI()

ICS.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 线上可以指定前端的url
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class Message(BaseModel):
    text: str

@ICS.get("/chat", response_class=HTMLResponse)
async def chat_page():
    with open("../frontend/home.html", "r", encoding="utf-8") as frontend_home_code:
        frontend_home = frontend_home_code.read()
    return frontend_home

@ICS.post("/chat")
async def chat_endpoint(msg: Message, request: Request):
    client_host = request.client.host
    logger.info("Incoming message from %s (%d chars)", client_host, len(msg.text))

    try:
        reply = stream_graph_updates(msg.text, client_host)
    except Exception:
        logger.exception("Graph execution failed for session %s", client_host)
        raise HTTPException(status_code=500, detail="Assistant failed to generate a response. Please try again.")

    return {"reply": reply}