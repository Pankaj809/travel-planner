import argparse
import os
import sys
import re
import json
from prompt import PROMPTS
from retrieval_db import get_db

from copilotkit import CopilotKitState
from copilotkit.langchain import copilotkit_customize_config
from copilotkit.langgraph import (copilotkit_exit)

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
# from langchain_community.embeddings import VolcanoEmbeddings
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
# from langchain_nvidia_ai_endpoints import ChatNVIDIA
# from langchain_deepseek import ChatDeepSeek
from langchain_core.runnables.history import RunnableWithMessageHistory
# from langchain_community.chat_models import VolcEngineMaasChat
# from openai import OpenAI
from langchain_core.messages import BaseMessage, AIMessage
from langchain_core.chat_history import BaseChatMessageHistory
from langchain.chat_models import init_chat_model

from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.memory import MemorySaver
from langgraph.types import Command

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import List

from typing import Annotated
from typing_extensions import TypedDict, Optional


file_questions = "./{标准问答对的位置}"
CHROMA_DIR_PATH = "./chroma"

load_dotenv()
store = {}
terminal_stdout = sys.stdout

MCPConfig = {
    #  mcp配置项
}

class State(CopilotKitState):
    mcp_config: Optional[MCPConfig]

graph_builder = StateGraph(State)


class InMemoryHistory(BaseChatMessageHistory, BaseModel):
    """In memory implementation of chat message history."""

    messages: List[BaseMessage] = Field(default_factory=list)

    def add_messages(self, messages: List[BaseMessage]) -> None:
        """Add a list of messages to the store"""
        self.messages.extend(messages)

    def clear(self) -> None:
        self.messages = []

def refine_que(state: State):
    print("refine_que")
    if state["messages"][-1].content == "":
        return {"messages": [state["messages"][-1]]}
    else:
        return Command(
            goto=END,
            update={"messages": add_messages},
        )

# Here we use a global variable to store the chat message history.
# This will make it easier to inspect it to see the underlying results.
def search_info(state: State):
    query = state["messages"][0].content
    # print(query)
    # print("***********")
    context_text1 = get_db(query)
    if context_text1 == 0:
        unrelated = "No corresponding content found. If you have any questions, please consult a professional."
        return unrelated
    print("Get the vector db!")

    # client = ChatOpenAI(
    #       openai_api_key = os.environ.get("ARK_API_KEY"),
    #       openai_api_base="https://ark.cn-beijing.volces.com/api/v3",
    #       model_name="deepseek-r1-250120",
    #       max_tokens = None,
    #       temperature = 0)
    print("SILI_API_KEY=", os.environ.get("SILI_API_KEY"))

    client = ChatOpenAI(
          openai_api_key = os.environ.get("SILI_API_KEY"),
          openai_api_base="https://api.siliconflow.cn/",
          model_name="Qwen/Qwen2.5-Coder-32B-Instruct",
          max_tokens = None,
          temperature = 0)

    prompt_init = ChatPromptTemplate.from_messages([
        ("system", PROMPTS["role_prompts"]),
        # MessagesPlaceholder(variable_name="history"),  # 历史消息占位符
        ("human", "{question}"),  # 用户输入
    ])

    chain = prompt_init | client

    # chain_with_history = RunnableWithMessageHistory(
    #         chain,
    #         get_by_session_id,
    #         input_messages_key="question",
    #         history_messages_key="history",
    #     )

    prompt_template = ChatPromptTemplate.from_template(PROMPTS["customer_questions"])
    prompt_question = prompt_template.format(knowledge_base=context_text1, question=query)
    # 调用链并传入会话 ID
    # session_id = state["thread_id"]
    # response_question = chain_with_history.invoke(
    #     {
    #         "question": prompt_question
    #     },
    #     config={"configurable": {"session_id": "session_id"}}
    # )
    response_question = chain.invoke(prompt_question)
    print(response_question.content)
    result = {
        "messages": [response_question]
    }
    return result

def print_tofront(state: State):
    print("print_tofront")
    return {"messages": [state["messages"][-1]]}

def get_by_session_id(session_id: str) -> BaseChatMessageHistory:
    if session_id not in store:
        store[session_id] = InMemoryHistory()
    return store[session_id]

def query_rag(state: State):
    # Init vector DB
    # embedding_fn = NVIDIAEmbeddings(model="NV-Embed-QA")
    context_text1 = get_db(query)
    if context_text1 == 0:
        unrelated = "No corresponding content found. If you have any questions, please consult a professional."
        return unrelated
    print("Get the vector db!")

    # client = ChatOpenAI(
    #       openai_api_key = os.environ.get("ARK_API_KEY"),
    #       openai_api_base="https://ark.cn-beijing.volces.com/api/v3",
    #       model_name="deepseek-r1-250120",
    #       max_tokens = None,
    #       temperature = 0)
    print("SILI_API_KEY=", os.environ.get("SILI_API_KEY"))

    client = ChatOpenAI(
          openai_api_key = os.environ.get("SILI_API_KEY"),
          openai_api_base="https://api.siliconflow.cn/",
          model_name="Qwen/Qwen2.5-Coder-32B-Instruct",
          max_tokens = None,
          temperature = 0)

    prompt_init = ChatPromptTemplate.from_messages([
        ("system", PROMPTS["role_prompts"]),
        MessagesPlaceholder(variable_name="history"),  # 历史消息占位符
        ("human", "{question}"),  # 用户输入
    ])

    chain = prompt_init | client

    chain_with_history = RunnableWithMessageHistory(
            chain,
            get_by_session_id,
            input_messages_key="question",
            history_messages_key="history",
        )

    prompt_template = ChatPromptTemplate.from_template(PROMPTS["customer_questions"])
    prompt_question = prompt_template.format(knowledge_base=context_text1, question=query)
    # 调用链并传入会话 ID
    session_id = client_ip
    response_question = chain_with_history.invoke(
        {
            "question": prompt_question
        },
        config={"configurable": {"session_id": session_id}}
    )
    # response_question = client.invoke(prompt_question)
    print(response_question.content)
    return response_question.content


graph_builder.add_node("refine_que", refine_que)
graph_builder.add_node("search_info", search_info)
graph_builder.add_node("print_tofront", print_tofront)
# graph_builder.set_entry_point("refine_que")
graph_builder.add_edge(START, "search_info")
# graph_builder.add_edge("print_tofront", END)
graph = graph_builder.compile(MemorySaver())

def stream_graph_updates(user_input: str, client_ip:str):
    user_info = State(
        messages = [user_input],
    )
    config = {"configurable": {"thread_id": client_ip}}
    output_messages = []
    for event in graph.stream(user_info, config):
        for value in event.values():
            message_content = value["messages"][-1].content
            print("Assistant:", message_content)
            return message_content
            # output_messages.append(message_content)
    # return output_messages


def main():
    # 平常调试时候不用走前端界面 python这个query_data就行 
    with open(file_questions, 'r', encoding='utf-8') as file:
        query_text = file.read()
    query_rag(query_text, "127.0.0.1")

if __name__ == "__main__":
    main()
