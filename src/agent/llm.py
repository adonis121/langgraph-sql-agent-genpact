"""The chat model used by the agent."""
import os

from langchain_openai import ChatOpenAI


def get_llm() -> ChatOpenAI:
    model = os.getenv("OPENAI_MODEL")
    if not model:
        raise RuntimeError("OPENAI_MODEL is not set. Add it to .env, e.g. OPENAI_MODEL=gpt-4o-mini")
    return ChatOpenAI(model=model, temperature=0)
