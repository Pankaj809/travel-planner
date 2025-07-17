from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from query_data import query_rag

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
    # 你的后续处理...
    LLM_response = query_rag(msg.text, request.client.host)
    response = f"{LLM_response}"
    return {"reply": response}