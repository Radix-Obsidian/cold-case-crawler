"""Custom exception classes for Murder Index."""


class ColdCaseCrawlerError(Exception):
    """Base exception for all application errors."""

    pass


class CrawlerError(ColdCaseCrawlerError):
    """Errors from the crawler service."""

    pass


class FirecrawlAPIError(CrawlerError):
    """Firecrawl API returned an error."""

    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        super().__init__(f"Firecrawl error {status_code}: {message}")


class DebateEngineError(ColdCaseCrawlerError):
    """Errors from the debate engine."""

    pass


class AgentResponseError(DebateEngineError):
    """PydanticAI agent failed to generate valid response."""

    pass


class AudioServiceError(ColdCaseCrawlerError):
    """Errors from the audio service."""

    pass


class ElevenLabsAPIError(AudioServiceError):
    """ElevenLabs API returned an error."""

    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        super().__init__(f"ElevenLabs error {status_code}: {message}")


class VideoServiceError(ColdCaseCrawlerError):
    """Errors from the video service."""

    pass


class CreatomateAPIError(VideoServiceError):
    """Creatomate API returned an error."""

    def __init__(self, status_code: int, message: str) -> None:
        self.status_code = status_code
        super().__init__(f"Creatomate error {status_code}: {message}")
