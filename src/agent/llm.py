"""The chat model used by the agent."""
import os
import re

from langchain_openai import ChatOpenAI


def get_llm() -> ChatOpenAI:
    model = os.getenv("OPENAI_MODEL")
    if not model:
        raise RuntimeError("OPENAI_MODEL is not set. Add it to .env, e.g. OPENAI_MODEL=gpt-4o-mini")
    return ChatOpenAI(model=model, temperature=0)


def strip_code_fences(text: str) -> str:
    """Remove the markdown code fences the model sometimes wraps around SQL or JSON."""
    match = re.search(r"```(?:\w+)?\s*(.*?)```", text, re.DOTALL)
    return (match.group(1) if match else text).strip()
