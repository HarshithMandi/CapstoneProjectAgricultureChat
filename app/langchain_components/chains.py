from typing import Any
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnablePassthrough
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain.chains import create_retrieval_chain


def get_agriculture_prompt() -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages([
        ("system", """You are an AI-powered agriculture assistant. Use the provided context to answer questions about farming, crops, diseases, fertilizers, soil conditions, irrigation, and best practices.

Context information is below:
{context}

Previous conversation:
{chat_history}

Instructions:
1. Only use information from the context to answer questions
2. If the context doesn't have enough information, say so clearly
3. Cite sources when possible
4. Be specific and detailed in your responses
5. Do not make up information"""),
        ("human", "{input}"),
    ])


def get_no_context_prompt() -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages([
        ("system", """You are an AI-powered agriculture assistant. Answer the user's question based on your knowledge.

Previous conversation:
{chat_history}

If you're unsure about something, acknowledge the limitation."""),
        ("human", "{input}"),
    ])


def format_docs(docs):
    return "\n\n".join(f"Source: {doc.metadata.get('source', 'unknown')}\n{doc.page_content}" for doc in docs)