class ApplicationError(Exception):
    def __init__(self, message: str, details: dict | None = None):
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class DocumentNotFoundError(ApplicationError):
    pass


class SessionNotFoundError(ApplicationError):
    pass


class IngestionError(ApplicationError):
    pass


class RetrievalError(ApplicationError):
    pass


class LLMError(ApplicationError):
    pass