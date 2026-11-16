"""A fake chat model for tests: returns scripted replies in order, no API calls.

Every node talks to the model the same way, llm.invoke(prompt).content, so scripted
strings are enough: planner JSON, SQL, answer text.
"""
from langchain_core.messages import AIMessage


class FakeLLM:
    def __init__(self, replies: list[str]):
        self.replies = list(replies)
        self.prompts: list[str] = []  # every prompt the graph sent, in order

    def invoke(self, prompt: str) -> AIMessage:
        self.prompts.append(prompt)
        if not self.replies:
            # A loud failure: the graph made an LLM call the test did not expect.
            raise AssertionError(f"FakeLLM: no reply left for prompt:\n{prompt[:300]}")
        return AIMessage(content=self.replies.pop(0))

    @property
    def remaining(self) -> int:
        return len(self.replies)
