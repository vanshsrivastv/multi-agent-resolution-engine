import os

from dotenv import load_dotenv
from groq import APIConnectionError, Groq, InternalServerError, RateLimitError
from langsmith import get_current_run_tree, traceable

from app.retry import with_retries

load_dotenv()

DEFAULT_MODEL = "openai/gpt-oss-120b"

# Network/rate-limit/server issues are worth a retry. Anything else (bad
# request, auth, etc.) is a config/code problem retrying won't fix.
GROQ_TRANSIENT = (APIConnectionError, RateLimitError, InternalServerError)


@traceable(run_type="llm", name="groq_chat_completion")
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

    # ask() only returns the text, but the trace should still show real
    # token usage - attach it to the current run directly rather than
    # changing what callers of ask() get back.
    run_tree = get_current_run_tree()
    if run_tree is not None and response.usage is not None:
        run_tree.metadata["usage_metadata"] = {
            "input_tokens": response.usage.prompt_tokens,
            "output_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
        }

    return response.choices[0].message.content
