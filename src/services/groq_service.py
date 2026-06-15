"""Groq client + rizz prompt."""
import random
import logging
from groq import AsyncGroq
from groq import APIError, RateLimitError, APITimeoutError

from src.config import (
    GROQ_API_KEY,
    GROQ_MODEL,
    GROQ_TEMPERATURE,
    GROQ_MAX_TOKENS,
    GROQ_TIMEOUT,
    SYSTEM_PROMPT,
    FALLBACK_LINES,
)

logger = logging.getLogger(__name__)


class GroqService:
    """Async Groq client for generating pickup lines."""

    def __init__(self) -> None:
        if not GROQ_API_KEY:
            raise RuntimeError("GROQ_API_KEY is empty")
        self._client = AsyncGroq(api_key=GROQ_API_KEY)
        self._last_model = GROQ_MODEL

    @property
    def model(self) -> str:
        return self._last_model

    def update_model(self, model_name: str) -> str:
        self._last_model = model_name
        logger.info("Model switched to %s", model_name)
        return self._last_model

    async def generate_rizz(self, context: str, tone: str | None = None) -> str:
        """Generate a pickup/rizz line for the given conversation context.

        Returns the generated line (str), or a random fallback line on error.
        """
        user_prompt = self._build_user_prompt(context, tone)

        try:
            response = await self._client.chat.completions.create(
                model=self._last_model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=GROQ_TEMPERATURE,
                max_tokens=GROQ_MAX_TOKENS,
                timeout=GROQ_TIMEOUT,
            )

            raw = response.choices[0].message.content
            if not raw or not raw.strip():
                logger.warning("Groq returned empty — using fallback")
                return self._fallback()

            return raw.strip()

        except RateLimitError:
            logger.warning("Groq rate limited — using fallback")
            return self._fallback()
        except APITimeoutError:
            logger.warning("Groq timeout — using fallback")
            return self._fallback()
        except APIError as exc:
            logger.error("Groq API error: %s", exc)
            return self._fallback()
        except Exception as exc:
            logger.exception("Unexpected Groq error: %s", exc)
            return self._fallback()

    def _build_user_prompt(self, context: str, tone: str | None = None) -> str:
        tone_instruction = ""
        if tone:
            tone_instruction = f"Make it {tone} in tone. "
        return (
            f"Conversation context:\n"
            f"\"{context}\"\n\n"
            f"{tone_instruction}"
            f"Generate a pickup line that fits this context:"
        )

    def _fallback(self) -> str:
        return random.choice(FALLBACK_LINES)
