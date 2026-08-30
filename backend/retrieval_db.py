import argparse
import os
import sys
import re
import json

from langchain_openai import OpenAIEmbeddings

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

import config
from logging_config import get_logger

logger = get_logger(__name__)

RELEVANCE_THRESHOLD = 0.5
load_dotenv()


def get_db(query):
    embedding_fn = OpenAIEmbeddings(
        model=config.EMBEDDING_MODEL,
        openai_api_key = config.LLM_API_KEY,
        openai_api_base = config.LLM_BASE_URL
    ) # 嵌入式模型
    db_chroma = Chroma(collection_name = config.CHROMA_COLLECTION_NAME, persist_directory=config.CHROMA_DIR_PATH, embedding_function=embedding_fn)

    logger.debug("Querying vector db for: %r", query)
    # 返回匹配程度最高的25个块
    results1 = db_chroma.similarity_search_with_score(query, 25)

    logger.debug("Vector db returned %d result(s)", len(results1))

    if len(results1) == 0 or results1[0][1] < RELEVANCE_THRESHOLD:
        # 这一步检索了 客户的问题与当前知识库的相关性
        return 0

    context_text1 = "\n\n---\n\n".join([doc.page_content for doc, _score in results1])
    return context_text1