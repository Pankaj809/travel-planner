import os
import sys

from prompt import PROMPTS
from retrieval_db import get_db

from copilotkit import CopilotKitState

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
# from langchain_community.embeddings import VolcanoEmbeddings
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
# from langchain_nvidia_ai_endpoints import ChatNVIDIA
# from langchain_deepseek import ChatDeepSeek
from langchain_core.runnables.history import RunnableWithMessageHistory
# from langchain_community.chat_models import VolcEngineMaasChat
# from openai import OpenAI
from langchain_core.messages import BaseMessage, HumanMessage, AIMessage
from langchain_core.chat_history import BaseChatMessageHistory

from langgraph.graph import StateGraph, START, END

from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import List

file_questions = "./{标准问答对的位置}"
CHROMA_DIR_PATH = "./chroma"

load_dotenv()
store = {}
terminal_stdout = sys.stdout

class State(CopilotKitState):
    messages: list[BaseMessage]
    thread_id: str

graph_builder = StateGraph(State)


class InMemoryHistory(BaseChatMessageHistory, BaseModel):
    """In memory implementation of chat message history."""

    messages: List[BaseMessage] = Field(default_factory=list)

    def add_messages(self, messages: List[BaseMessage]) -> None:
        """Add a list of messages to the store"""
        self.messages.extend(messages)

    def clear(self) -> None:
        self.messages = []

def get_by_session_id(session_id: str) -> BaseChatMessageHistory:
    if session_id not in store:
        store[session_id] = InMemoryHistory()
    return store[session_id]

def refine_que(state: State):
    if state["messages"][-1] == "":
        return state
    else:
        return state

def check_related(state: State):
    embedding_fn = OpenAIEmbeddings(
        model="Pro/BAAI/bge-m3",
        openai_api_key = os.environ.get("SILI_API_KEY"),
        openai_api_base ="https://api.siliconflow.cn/v1"
    ) # 嵌入式模型
    db_chroma = Chroma(collection_name = "chromadb", persist_directory=CHROMA_DIR_PATH, embedding_function=embedding_fn)

    print("Querying the vector db ....")
    # Search vector DB
    # 返回匹配程度最高的25个块
    query = state["messages"][-1].content
    results1 = db_chroma.similarity_search_with_score(query, 3)

    print(f"Length of results {len(results1)}")

    if len(results1) == 0 or results1[0][1] < 0.5:
        # 这一步检索了 客户的问题与当前知识库的相关性
        # return False
        return True
    else:
        return True

# Here we use a global variable to store the chat message history.
# This will make it easier to inspect it to see the underlying results.
def search_info(state: State):
    query = state["messages"][-1].content
    # print(query)
    # print("***********")
    context_text1 = get_db(query)
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
    session_id = state["thread_id"]
    response_question = chain_with_history.invoke(
        {
            "question": prompt_question
        },
        config={"configurable": {"session_id": session_id}}
    )
    # response_question = chain.invoke(prompt_question)
    print(response_question.content)
    result = {
        "messages": [response_question]
    }
    return result

def print_tofront(state: State):
    print("print_tofront")
    return {"messages": [state["messages"][-1]]}


# def query_rag(state: State):
#     query = state["messages"][0].content
#     # Init vector DB
#     # embedding_fn = NVIDIAEmbeddings(model="NV-Embed-QA")
#     context_text1 = get_db(query)
#     print("Get the vector db!")

#     # client = ChatOpenAI(
#     #       openai_api_key = os.environ.get("ARK_API_KEY"),
#     #       openai_api_base="https://ark.cn-beijing.volces.com/api/v3",
#     #       model_name="deepseek-r1-250120",
#     #       max_tokens = None,
#     #       temperature = 0)
#     print("SILI_API_KEY=", os.environ.get("SILI_API_KEY"))

#     client = ChatOpenAI(
#           openai_api_key = os.environ.get("SILI_API_KEY"),
#           openai_api_base="https://api.siliconflow.cn/",
#           model_name="Qwen/Qwen2.5-Coder-32B-Instruct",
#           max_tokens = None,
#           temperature = 0)

#     prompt_init = ChatPromptTemplate.from_messages([
#         # ("system", PROMPTS["role_prompts"]),
#         ("system", PROMPTS["role_prompts"]),
#         MessagesPlaceholder(variable_name="history"),  # 历史消息占位符
#         ("human", "{question}"),  # 用户输入
#     ])

#     chain = prompt_init | client

#     chain_with_history = RunnableWithMessageHistory(
#             chain,
#             get_by_session_id,
#             input_messages_key="question",
#             history_messages_key="history",
#         )

#     prompt_template = ChatPromptTemplate.from_template(PROMPTS["customer_questions"])
#     prompt_question = prompt_template.format(knowledge_base=context_text1, question=query)
#     # 调用链并传入会话 ID
#     # session_id = client_ip
#     session_id = "session_id"
#     response_question = chain_with_history.invoke(
#         {
#             "question": prompt_question
#         },
#         config={"configurable": {"session_id": session_id}}
#     )
#     # response_question = client.invoke(prompt_question)
#     print(response_question.content)
#     return response_question.content


graph_builder.add_node("refine_que", refine_que)
graph_builder.add_node("search_info", search_info)
graph_builder.add_node("print_tofront", print_tofront)

graph_builder.add_edge(START, "refine_que")
graph_builder.add_conditional_edges("refine_que", check_related, {True: "search_info", False: "search_info"})
graph_builder.add_edge("search_info", "print_tofront")
graph_builder.add_edge("print_tofront", END)
graph = graph_builder.compile()

def stream_graph_updates(user_input: str, client_ip:str):

    user_info = State(
        messages=[HumanMessage(content=user_input)],
        thread_id = client_ip)
    config = {"configurable": {"thread_id": client_ip}}

    # output_messages = []
    for event in graph.stream(user_info, config):
        for value in event.values():
            message_content = value["messages"][-1].content
    print("Assistant:", message_content)
    return message_content
            # output_messages.append(message_content)
    # return output_messages


# def main():
#     # 平常调试时候不用走前端界面 python这个query_data就行 
#     with open(file_questions, 'r', encoding='utf-8') as file:
#         query_text = file.read()
#     query_rag(query_text, "127.0.0.1")

# if __name__ == "__main__":
#     main()
