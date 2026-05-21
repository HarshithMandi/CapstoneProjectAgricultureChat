from app.services.chat_service import ChatService
from app.langchain_components.embeddings import OpenRouterEmbeddings


chat_service: ChatService | None = None


def get_chat_service() -> ChatService:
    global chat_service
    if chat_service is None:
        chat_service = ChatService()
    return chat_service


async def close_chat_service():
    global chat_service
    if chat_service:
        await chat_service.close()
        chat_service = None