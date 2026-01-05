# Technical Standards: Murder Index

> *Python-native. Async-first. Type-safe. No exceptions.*

---

## Golden Rules

1. **NO TypeScript** — This is a Python-only project
2. **Async everywhere** — All I/O operations use `async/await`
3. **Pydantic for everything** — Data validation is non-negotiable
4. **Official SDKs only** — Use documented APIs, no workarounds

---

## Technology Stack

### Core Framework
```
fastapi>=0.109.0      # Async web framework
uvicorn[standard]     # ASGI server
pydantic>=2.5.0       # Data validation
python-dotenv         # Environment management
```

### AI & Agents
```
pydantic-ai>=0.0.10   # Agent framework (official Pydantic)
anthropic>=0.18.0     # Claude API client
```

### External Services
```
firecrawl-py>=1.0.0   # Web scraping (official SDK)
elevenlabs>=1.0.0     # Voice synthesis (official SDK)
supabase>=2.0.0       # Database & storage (official SDK)
httpx>=0.26.0         # Async HTTP client (for Creatomate)
```

### Testing
```
pytest>=8.0.0
pytest-asyncio>=0.23.0
hypothesis>=6.92.0    # Property-based testing
respx>=0.20.0         # HTTP mocking
pytest-cov>=4.1.0     # Coverage reporting
```

---

## Project Structure

```
cold-case-crawler/
├── src/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application
│   ├── config.py               # Settings & environment
│   ├── models/
│   │   ├── __init__.py
│   │   ├── case.py             # CaseFile, Evidence
│   │   ├── script.py           # PodcastScript, DialogueLine
│   │   └── job.py              # JobStatus
│   ├── services/
│   │   ├── __init__.py
│   │   ├── crawler.py          # CrawlerService
│   │   ├── debate.py           # DebateEngine
│   │   ├── audio.py            # AudioService
│   │   └── video.py            # VideoService
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── thorne.py           # Dr. Thorne agent config
│   │   └── maya.py             # Maya Vance agent config
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── retry.py            # Retry decorator
│   │   └── errors.py           # Custom exceptions
│   └── api/
│       ├── __init__.py
│       ├── routes.py           # API endpoints
│       └── deps.py             # Dependencies
├── tests/
│   ├── __init__.py
│   ├── conftest.py             # Fixtures
│   ├── unit/
│   │   ├── test_models.py
│   │   └── test_utils.py
│   ├── integration/
│   │   ├── test_crawler.py
│   │   └── test_debate.py
│   └── property/
│       ├── test_validation.py
│       └── test_transforms.py
├── .env.example
├── pyproject.toml
├── requirements.txt
└── README.md
```

---

## Code Style

### PEP 8 Compliance

```toml
# pyproject.toml
[tool.black]
line-length = 100
target-version = ['py311']

[tool.ruff]
line-length = 100
select = ["E", "F", "I", "N", "W", "UP"]

[tool.mypy]
python_version = "3.11"
strict = true
```

### Naming Conventions

```python
# Classes: PascalCase
class CrawlerService:
    pass

class CaseFile(BaseModel):
    pass

# Functions/methods: snake_case
async def search_cold_cases(query: str) -> list[CaseFile]:
    pass

def _parse_evidence(markdown: str) -> list[Evidence]:
    pass

# Constants: SCREAMING_SNAKE_CASE
MAX_RETRY_ATTEMPTS = 3
BASE_DELAY_SECONDS = 1.0
ELEVENLABS_MODEL_ID = "eleven_v3"

# Type aliases: PascalCase
Speaker = Literal['dr_aris_thorne', 'maya_vance']
EmotionTag = Literal['scoffs', 'excited', 'whispers']
```

### Import Organization

```python
# Standard library
import asyncio
from datetime import datetime
from typing import Literal, Optional

# Third-party
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from pydantic_ai import Agent

# Local
from src.models import CaseFile, PodcastScript
from src.services import CrawlerService
from src.utils.retry import with_retry
```

---

## Async Patterns

### Always Async for I/O

```python
# ✅ CORRECT - async for external calls
async def fetch_case(url: str) -> CaseFile:
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return parse_response(response)

# ❌ WRONG - blocking I/O
def fetch_case(url: str) -> CaseFile:
    response = requests.get(url)  # BLOCKS EVENT LOOP
    return parse_response(response)
```

### Concurrent Execution

```python
# ✅ CORRECT - parallel execution
async def process_urls(urls: list[str]) -> list[CaseFile]:
    tasks = [fetch_case(url) for url in urls]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return [r for r in results if isinstance(r, CaseFile)]

# ❌ WRONG - sequential when parallel is possible
async def process_urls(urls: list[str]) -> list[CaseFile]:
    results = []
    for url in urls:
        results.append(await fetch_case(url))  # SLOW
    return results
```

### Context Managers

```python
# ✅ CORRECT - proper resource management
async def synthesize_audio(text: str) -> bytes:
    async with AsyncElevenLabs(api_key=settings.elevenlabs_key) as client:
        return await client.generate(text=text, model_id="eleven_v3")

# ❌ WRONG - resource leak potential
async def synthesize_audio(text: str) -> bytes:
    client = AsyncElevenLabs(api_key=settings.elevenlabs_key)
    return await client.generate(text=text, model_id="eleven_v3")
    # Client never closed!
```

---

## Pydantic Patterns

### Model Definition

```python
from pydantic import BaseModel, Field, field_validator
from typing import Literal
from datetime import datetime

class DialogueLine(BaseModel):
    """A single line of podcast dialogue."""
    
    speaker: Literal['dr_aris_thorne', 'maya_vance']
    text: str = Field(min_length=1, max_length=5000)
    emotion_tag: Literal['scoffs', 'excited', 'whispers', 'neutral'] = 'neutral'
    
    @field_validator('text')
    @classmethod
    def text_not_whitespace(cls, v: str) -> str:
        if not v.strip():
            raise ValueError('text cannot be only whitespace')
        return v
    
    def to_elevenlabs_format(self) -> str:
        """Format for ElevenLabs v3 synthesis."""
        if self.emotion_tag == 'neutral':
            return self.text
        return f"[{self.emotion_tag}] {self.text}"
```

### Nested Models

```python
class PodcastScript(BaseModel):
    """Complete podcast episode script."""
    
    script_id: str = Field(min_length=1)
    case_id: str = Field(min_length=1)
    episode_title: str = Field(min_length=1, max_length=200)
    chapters: list[DialogueLine] = Field(min_length=1)
    social_hooks: list[str] = Field(default_factory=list, max_length=10)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "script_id": "script-001",
                    "case_id": "case-001",
                    "episode_title": "The Minnesota Mystery",
                    "chapters": [
                        {"speaker": "maya_vance", "text": "Welcome back...", "emotion_tag": "excited"}
                    ],
                    "social_hooks": ["The alibi fell apart."]
                }
            ]
        }
    }
```

### Settings Management

```python
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    """Application settings from environment."""
    
    # API Keys
    firecrawl_api_key: str
    anthropic_api_key: str
    elevenlabs_api_key: str
    creatomate_api_key: str
    
    # Supabase
    supabase_url: str
    supabase_key: str
    
    # Configuration
    log_level: str = "INFO"
    max_retry_attempts: int = 3
    base_delay_seconds: float = 1.0
    
    # ElevenLabs
    elevenlabs_model: str = "eleven_v3"
    thorne_voice_id: str = ""
    maya_voice_id: str = ""
    
    model_config = {"env_file": ".env"}

@lru_cache
def get_settings() -> Settings:
    return Settings()
```

---

## Error Handling

### Custom Exceptions

```python
# src/utils/errors.py

class ColdCaseCrawlerError(Exception):
    """Base exception for all application errors."""
    pass

class CrawlerError(ColdCaseCrawlerError):
    """Errors from the crawler service."""
    pass

class FirecrawlAPIError(CrawlerError):
    """Firecrawl API returned an error."""
    def __init__(self, status_code: int, message: str):
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
    def __init__(self, status_code: int, message: str):
        self.status_code = status_code
        super().__init__(f"ElevenLabs error {status_code}: {message}")

class VideoServiceError(ColdCaseCrawlerError):
    """Errors from the video service."""
    pass

class CreatomateAPIError(VideoServiceError):
    """Creatomate API returned an error."""
    pass
```

### Retry Decorator

```python
# src/utils/retry.py

import asyncio
from functools import wraps
from typing import TypeVar, Callable, Any
import logging

logger = logging.getLogger(__name__)
T = TypeVar('T')

def with_retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    exceptions: tuple[type[Exception], ...] = (Exception,)
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator for exponential backoff retry logic.
    
    Args:
        max_attempts: Maximum number of retry attempts
        base_delay: Base delay in seconds (doubles each attempt)
        exceptions: Tuple of exception types to catch
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            last_exception: Exception | None = None
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_attempts - 1:
                        delay = base_delay * (2 ** attempt)
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_attempts} failed: {e}. "
                            f"Retrying in {delay}s..."
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(f"All {max_attempts} attempts failed: {e}")
            
            raise last_exception  # type: ignore
        return wrapper
    return decorator
```

### FastAPI Error Handling

```python
# src/api/routes.py

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

app = FastAPI(title="Murder Index API")

@app.exception_handler(ValidationError)
async def validation_exception_handler(request: Request, exc: ValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Validation error",
            "errors": exc.errors()
        }
    )

@app.exception_handler(ColdCaseCrawlerError)
async def app_exception_handler(request: Request, exc: ColdCaseCrawlerError):
    return JSONResponse(
        status_code=500,
        content={
            "detail": str(exc),
            "type": type(exc).__name__
        }
    )
```

---

## PydanticAI Agent Patterns

### Agent Definition

```python
# src/agents/thorne.py

from pydantic_ai import Agent
from src.models import DialogueLine, CaseFile

DR_THORNE_SYSTEM_PROMPT = """
You are Dr. Aris Thorne, a forensic psychologist...
[Full prompt from brand.md]
"""

def create_thorne_agent() -> Agent[CaseFile, DialogueLine]:
    """Create the Dr. Thorne agent with proper configuration."""
    return Agent(
        'anthropic:claude-3-5-sonnet-20241022',
        system_prompt=DR_THORNE_SYSTEM_PROMPT,
        result_type=DialogueLine,
        retries=2
    )
```

### Agent Usage

```python
# src/services/debate.py

from pydantic_ai import Agent
from src.agents.thorne import create_thorne_agent
from src.agents.maya import create_maya_agent

class DebateEngine:
    def __init__(self):
        self.thorne = create_thorne_agent()
        self.maya = create_maya_agent()
    
    async def generate_exchange(
        self, 
        case: CaseFile, 
        context: list[DialogueLine]
    ) -> tuple[DialogueLine, DialogueLine]:
        """Generate one exchange between hosts."""
        
        # Maya speaks first with context
        maya_prompt = self._build_prompt(case, context, "maya")
        maya_result = await self.maya.run(maya_prompt, deps=case)
        
        # Thorne responds
        context_with_maya = context + [maya_result.data]
        thorne_prompt = self._build_prompt(case, context_with_maya, "thorne")
        thorne_result = await self.thorne.run(thorne_prompt, deps=case)
        
        return maya_result.data, thorne_result.data
```

---

## Testing Patterns

### Unit Tests

```python
# tests/unit/test_models.py

import pytest
from pydantic import ValidationError
from src.models import DialogueLine, PodcastScript

class TestDialogueLine:
    def test_valid_dialogue(self):
        line = DialogueLine(
            speaker="maya_vance",
            text="This is compelling evidence.",
            emotion_tag="excited"
        )
        assert line.speaker == "maya_vance"
        assert line.emotion_tag == "excited"
    
    def test_invalid_speaker_rejected(self):
        with pytest.raises(ValidationError) as exc_info:
            DialogueLine(
                speaker="unknown_host",  # Invalid
                text="Hello"
            )
        assert "speaker" in str(exc_info.value)
    
    def test_empty_text_rejected(self):
        with pytest.raises(ValidationError):
            DialogueLine(speaker="maya_vance", text="")
    
    def test_whitespace_text_rejected(self):
        with pytest.raises(ValidationError):
            DialogueLine(speaker="maya_vance", text="   ")
    
    def test_elevenlabs_format_with_tag(self):
        line = DialogueLine(
            speaker="dr_aris_thorne",
            text="The evidence is clear.",
            emotion_tag="scoffs"
        )
        assert line.to_elevenlabs_format() == "[scoffs] The evidence is clear."
    
    def test_elevenlabs_format_neutral(self):
        line = DialogueLine(
            speaker="dr_aris_thorne",
            text="The evidence is clear.",
            emotion_tag="neutral"
        )
        assert line.to_elevenlabs_format() == "The evidence is clear."
```

### Property-Based Tests

```python
# tests/property/test_validation.py

from hypothesis import given, strategies as st
from pydantic import ValidationError
from src.models import DialogueLine

# Strategy for valid speakers
valid_speakers = st.sampled_from(['dr_aris_thorne', 'maya_vance'])

# Strategy for valid emotion tags
valid_tags = st.sampled_from(['scoffs', 'excited', 'whispers', 'neutral'])

# Strategy for non-empty text
valid_text = st.text(min_size=1, max_size=1000).filter(lambda x: x.strip())

@given(speaker=valid_speakers, text=valid_text, tag=valid_tags)
def test_valid_dialogue_always_creates(speaker, text, tag):
    """Property: Valid inputs always create valid DialogueLine."""
    line = DialogueLine(speaker=speaker, text=text, emotion_tag=tag)
    assert line.speaker == speaker
    assert line.text == text
    assert line.emotion_tag == tag

@given(text=st.text().filter(lambda x: not x.strip()))
def test_whitespace_text_always_rejected(text):
    """Property: Whitespace-only text always raises ValidationError."""
    with pytest.raises(ValidationError):
        DialogueLine(speaker="maya_vance", text=text)

@given(speaker=st.text().filter(lambda x: x not in ['dr_aris_thorne', 'maya_vance']))
def test_invalid_speaker_always_rejected(speaker):
    """Property: Invalid speakers always raise ValidationError."""
    with pytest.raises(ValidationError):
        DialogueLine(speaker=speaker, text="Valid text")
```

### Integration Tests with Mocks

```python
# tests/integration/test_crawler.py

import pytest
import respx
from httpx import Response
from src.services.crawler import CrawlerService

@pytest.fixture
def crawler_service():
    return CrawlerService(
        firecrawl_api_key="test-key",
        supabase_client=None  # Mock in tests
    )

@respx.mock
@pytest.mark.asyncio
async def test_search_cold_cases(crawler_service):
    # Mock Firecrawl API response
    respx.post("https://api.firecrawl.dev/v1/search").mock(
        return_value=Response(200, json={
            "success": True,
            "data": [{
                "url": "https://example.com/case",
                "markdown": "# Cold Case: Jane Doe\n\nLocation: Minnesota...",
                "metadata": {"title": "Cold Case: Jane Doe"}
            }]
        })
    )
    
    results = await crawler_service.search_cold_cases("Minnesota cold case")
    
    assert len(results) == 1
    assert results[0].location == "Minnesota"
```

---

## Environment Variables

```bash
# .env.example

# Required - API Keys
FIRECRAWL_API_KEY=fc-your-key-here
ANTHROPIC_API_KEY=sk-ant-your-key-here
ELEVENLABS_API_KEY=your-elevenlabs-key
CREATOMATE_API_KEY=your-creatomate-key

# Required - Supabase
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-supabase-anon-key

# Optional - Voice IDs (get from ElevenLabs dashboard)
THORNE_VOICE_ID=voice-id-for-thorne
MAYA_VOICE_ID=voice-id-for-maya

# Optional - Configuration
LOG_LEVEL=INFO
MAX_RETRY_ATTEMPTS=3
BASE_DELAY_SECONDS=1.0

# Optional - Creatomate
CREATOMATE_TEMPLATE_ID=your-template-id
```

---

## Running the Application

### Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run with auto-reload
uvicorn src.main:app --reload --port 8000

# Run tests
pytest tests/ -v --cov=src

# Type checking
mypy src/

# Linting
ruff check src/
black src/ --check
```

### Production

```bash
# Run with production settings
uvicorn src.main:app --host 0.0.0.0 --port 8000 --workers 4
```

---

## Checklist Before Commit

- [ ] All functions have type hints
- [ ] All I/O operations are async
- [ ] Pydantic models validate all inputs
- [ ] Custom exceptions used (not bare Exception)
- [ ] Retry logic on external API calls
- [ ] Tests pass (`pytest tests/`)
- [ ] Type check passes (`mypy src/`)
- [ ] Linting passes (`ruff check src/`)
- [ ] No hardcoded secrets
- [ ] Docstrings on public functions
