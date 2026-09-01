import os

from dotenv import load_dotenv
from groq import APIConnectionError, Groq, InternalServerError, RateLimitError

from app.retry import with_retries

load_dotenv()

DEFAULT_MODEL = "openai/gpt-oss-120b"

# Network/rate-limit/server issues are worth a retry. Anything else (bad
# request, auth, etc.) is a config/code problem retrying won't fix.
GROQ_TRANSIENT = (APIConnectionError, RateLimitError, InternalServerError)


def ask(system_prompt: str, user_message: str, model: str = DEFAULT_MODEL, max_tokens: int = 512) -> str:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not set. Add it to your .env file.")

    client = Groq(api_key=api_key)

    def _call():
        return client.chat.completions.create(
            model=model,
            max_tokens=max_tokens,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
        )

    response = with_retries(_call, GROQ_TRANSIENT)
    return response.choices[0].message.content
