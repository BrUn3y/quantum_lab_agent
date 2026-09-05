"""Shared chat-model configuration for all quantum agents."""

import os
from typing import Any

from dotenv import load_dotenv

from beeai_framework.backend import ChatModel, ChatModelError


load_dotenv()


DEFAULT_WATSONX_MODELS = {
    "DEVELOPER": "mistral-large-2512",
    "LAB": "mistralai/mistral-small-3-1-24b-instruct-2503",
    "STATUS": "mistralai/mistral-small-3-1-24b-instruct-2503",
    "COMPUTING": "mistralai/mistral-small-3-1-24b-instruct-2503",
    "EXPERIMENT": "mistralai/mistral-small-3-1-24b-instruct-2503",
}


def model_name(agent: str) -> str:
    """Return the configured BeeAI ``provider:model`` identifier."""
    agent = agent.upper()
    configured = os.getenv(f"{agent}_MODEL")
    if configured:
        return configured

    default = DEFAULT_WATSONX_MODELS[agent]
    watsonx_model = os.getenv(f"WATSONX_{agent}_MODEL", default)
    return f"watsonx:{watsonx_model}"


def create_chat_model(agent: str) -> ChatModel:
    """Create the configured BeeAI chat model for an agent."""
    return ChatModel.from_name(model_name(agent))


def explain_error(error: Exception) -> str:
    """Return the fullest available explanation for an exception.

    beeai_framework wraps provider failures (rate limits, timeouts, auth
    errors) in generic messages like "Chat Model error"; str(error) shows
    only that generic message, while FrameworkError.explain() walks the
    wrapped cause chain to surface what actually went wrong.
    """
    explain = getattr(error, "explain", None)
    return explain() if callable(explain) else str(error)


async def run_agent_with_retries(agent: Any, prompt: str, *, retries: int = 2) -> Any:
    """Run a ReActAgent, retrying on ChatModelError (e.g. an empty provider response).

    beeai_framework's own ReAct runner notes that empty LiteLLM responses are an
    expected, transient quirk it needs to handle - but ChatModelError always reports
    is_retryable=False, so the framework's internal retry logic never actually retries
    it. Retry here instead rather than failing the whole request on one blank completion.
    """
    for attempt in range(1, retries + 2):
        try:
            return await agent.run(prompt)
        except ChatModelError as e:
            if attempt > retries:
                raise
            print(f"⚠️ [Retry] LLM call failed ({explain_error(e)}); retrying ({attempt}/{retries})...")
