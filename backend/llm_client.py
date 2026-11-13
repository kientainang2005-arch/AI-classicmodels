# Gemini access with automatic fallback across API keys and models.
# Free-tier quotas are per project and per model, so when one (key, model) pair is
# exhausted (HTTP 429) we move to the next instead of failing the user's question.

import time

import google.generativeai as genai

from config import GEMINI_KEYS, GEMINI_MODELS

QUOTA_COOLDOWN_SEC = 30 * 60
_dead_until: dict[tuple[str, str], float] = {}


class AllQuotaExhausted(RuntimeError):
    pass


def _candidates():
    now = time.time()
    for model in GEMINI_MODELS:
        for key in GEMINI_KEYS:
            if _dead_until.get((key, model), 0) <= now:
                yield key, model


def _mark_dead(key: str, model: str, err: Exception) -> bool:
    """Return True if the error means 'try another key/model'."""
    text = str(err).lower()
    if "429" in text or "quota" in text:
        _dead_until[(key, model)] = time.time() + QUOTA_COOLDOWN_SEC
        return True
    if "404" in text or "no longer available" in text or "not found" in text:
        _dead_until[(key, model)] = float("inf")
        return True
    return False


def _run_with_fallback(action):
    """Call action(key, model) on each available pair until one succeeds."""
    for key, model in _candidates():
        try:
            genai.configure(api_key=key)
            return action(key, model)
        except Exception as e:
            if not _mark_dead(key, model, e):
                raise
    raise AllQuotaExhausted(
        "⚠️ Hết hạn mức Gemini miễn phí hôm nay (mỗi model chỉ ~20 request/ngày). "
        "Hãy thử lại sau, hoặc thêm API key/model khác trong file .env."
    )


def call_llm(prompt: str) -> str:
    return _run_with_fallback(
        lambda key, model: genai.GenerativeModel(model).generate_content(prompt).text
    )


def generate_sql(vn_instance, question: str) -> str:
    def action(key, model):
        vn_instance.chat_model = genai.GenerativeModel(model)
        return vn_instance.generate_sql(question)

    return _run_with_fallback(action)
