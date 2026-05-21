from langchain_core.prompts import ChatPromptTemplate


def get_agriculture_prompt() -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages([
    (
        "human",
        """Context information (may be empty):
{context}

Previous conversation:
{chat_history}

User question:
{input}""",
    ),
    ])


def get_no_context_prompt() -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages([
    (
        "human",
        """Previous conversation:
{chat_history}

User question:
{input}""",
    ),
    ])


def format_docs(docs):
    return "\n\n".join(f"Source: {doc.metadata.get('source', 'unknown')}\n{doc.page_content}" for doc in docs)