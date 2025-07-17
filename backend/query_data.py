import argparse
import os
import sys
import re
import json
from prompt import PROMPTS

from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_community.embeddings import VolcanoEmbeddings
from langchain_chroma import Chroma

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
# from langchain_nvidia_ai_endpoints import ChatNVIDIA
# from langchain_deepseek import ChatDeepSeek
from langchain_core.runnables.history import RunnableWithMessageHistory
# from langchain_community.chat_models import VolcEngineMaasChat
# from openai import OpenAI
from langchain_core.chat_history import BaseChatMessageHistory
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import List
from langchain_core.messages import BaseMessage, AIMessage

# file_path = "/home/jinyutong/nkocl_code/cuda_code.py"
file_questions = "./{标准问答对的位置}"
CHROMA_DIR_PATH = "./chroma"
RELEVANCE_THRESHOLD = 0.5
load_dotenv()
store = {}
terminal_stdout = sys.stdout

class InMemoryHistory(BaseChatMessageHistory, BaseModel):
    """In memory implementation of chat message history."""

    messages: List[BaseMessage] = Field(default_factory=list)

    def add_messages(self, messages: List[BaseMessage]) -> None:
        """Add a list of messages to the store"""
        self.messages.extend(messages)

    def clear(self) -> None:
        self.messages = []

# Here we use a global variable to store the chat message history.
# This will make it easier to inspect it to see the underlying results.

def get_by_session_id(session_id: str) -> BaseChatMessageHistory:
    if session_id not in store:
        store[session_id] = InMemoryHistory()
    return store[session_id]

def get_db(query):
    embedding_fn = OpenAIEmbeddings(
        model="Pro/BAAI/bge-m3",
        openai_api_key = os.environ.get("SILI_API_KEY"),
        openai_api_base ="https://api.siliconflow.cn/v1"
    ) # 嵌入式模型
    db_chroma = Chroma(collection_name = "chromadb", persist_directory=CHROMA_DIR_PATH, embedding_function=embedding_fn)

    print("Querying the vector db ....")
    # Search vector DB
    # 返回匹配程度最高的25个块
    results1 = db_chroma.similarity_search_with_score(query, 25)

    print(f"Length of results {len(results1)}")

    if len(results1) == 0 or results1[0][1] < RELEVANCE_THRESHOLD:
        # 这一步检索了 客户的问题与当前知识库的相关性
        return 0

    # context_text1 = "\n\n---\n\n".join([f"Score: {_score}\n{doc.page_content}"  for doc, _score in results1])
    context_text1 = "\n\n---\n\n".join([doc.page_content for doc, _score in results1])
    print(context_text1)
    return context_text1

def query_rag(query, client_ip):
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

    
def main():
    # 平常调试时候不用走前端界面 python这个query_data就行 
    with open(file_questions, 'r', encoding='utf-8') as file:
        query_text = file.read()
    query_rag(query_text, "127.0.0.1")
    


if __name__ == "__main__":
    main()
