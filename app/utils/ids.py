import uuid
from datetime import datetime


def generate_session_id() -> str:
    return f"sess_{uuid.uuid4().hex[:12]}"


def generate_message_id() -> str:
    return f"msg_{uuid.uuid4().hex[:12]}"


def generate_document_id() -> str:
    return f"doc_{uuid.uuid4().hex[:12]}"


def generate_chunk_id() -> str:
    return f"chunk_{uuid.uuid4().hex[:12]}"


def timestamp_ms() -> int:
    return int(datetime.utcnow().timestamp() * 1000)