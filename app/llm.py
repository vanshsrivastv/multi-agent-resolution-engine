import os

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

DEFAULT_MODEL = "openai/gpt-oss-120b"


def ask(system_prompt: str, user_message: str, model: str = DEFAULT_MODEL, max_tokens: int = 512) -> str:
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise RuntimeError("GROQ_API_KEY is not set. Add it to your .env file.")

    client = Groq(api_key=api_key)
    response = client.chat.completions.create(
        model=model,
        max_tokens=max_tokens,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
    )
    return response.choices[0].message.content
