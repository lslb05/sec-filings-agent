"""LLM client: compares two risk-factors sections via tool-calling.

Tool-calling instead of asking for JSON in free text: both Anthropic and
OpenAI validate the response's shape against a schema before returning it,
so there's no "the model forgot a comma" to handle here — just the content,
revalidated by Pydantic (an external boundary, even coming back already
structured). Both providers implement the same `LLMClient`; graph.py and
cli.py don't know which one is actually behind it.
"""

import json
from typing import Any, Literal, Protocol

import anthropic
import openai
from pydantic import BaseModel

_DEFAULT_MODEL_ANTHROPIC = "claude-sonnet-4-5"
_DEFAULT_MODEL_OPENAI = "gpt-5.4"
_MAX_TOKENS = 4096

_TOOL: dict[str, Any] = {
    "name": "record_changes",
    "description": (
        "Records the changes found between the two versions of a 10-K's "
        "risk factors section."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "changes": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "type": {
                            "type": "string",
                            "enum": ["added", "removed", "changed"],
                        },
                        "summary": {
                            "type": "string",
                            "description": "One sentence explaining the change.",
                        },
                        "citation": {
                            "type": "string",
                            "description": (
                                "A passage copied EXACTLY from the source text "
                                "that evidences the change."
                            ),
                        },
                        "filing": {
                            "type": "string",
                            "enum": ["old", "new"],
                            "description": "Which filing the citation was copied from.",
                        },
                    },
                    "required": ["type", "summary", "citation", "filing"],
                },
            },
        },
        "required": ["changes"],
    },
}


class RawChange(BaseModel):
    type: Literal["added", "removed", "changed"]
    summary: str
    citation: str
    filing: Literal["old", "new"]


class _ToolResponse(BaseModel):
    changes: list[RawChange]


class LLMClient(Protocol):
    """Injectable interface — tests use a fake client, without calling the API."""

    def compare(
        self, *, old_text: str, new_text: str, feedback: list[str]
    ) -> list[RawChange]: ...


class AnthropicClient:
    def __init__(self, *, api_key: str, model: str = _DEFAULT_MODEL_ANTHROPIC) -> None:
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def compare(
        self, *, old_text: str, new_text: str, feedback: list[str]
    ) -> list[RawChange]:
        # The Anthropic SDK's tool-use types are too deep to be worth
        # replicating here; the real schema is validated at runtime by the
        # API itself, and the response is revalidated by Pydantic below.
        response = self._client.messages.create(
            model=self._model,
            max_tokens=_MAX_TOKENS,
            tools=[_TOOL],
            tool_choice={"type": "tool", "name": "record_changes"},
            messages=[
                {
                    "role": "user",
                    "content": _build_prompt(old_text, new_text, feedback),
                }
            ],
        )  # type: ignore[call-overload]
        block = next(b for b in response.content if b.type == "tool_use")
        return _ToolResponse.model_validate(block.input).changes


class OpenAIClient:
    """Same contract as AnthropicClient, via OpenAI's function-calling.

    OpenAI uses `parameters` instead of `input_schema` and returns the
    function arguments as a JSON string, not an object — hence the
    `json.loads` before Pydantic revalidation, which AnthropicClient doesn't
    need.
    """

    def __init__(self, *, api_key: str, model: str = _DEFAULT_MODEL_OPENAI) -> None:
        self._client = openai.OpenAI(api_key=api_key)
        self._model = model

    def compare(
        self, *, old_text: str, new_text: str, feedback: list[str]
    ) -> list[RawChange]:
        response = self._client.chat.completions.create(
            model=self._model,
            max_completion_tokens=_MAX_TOKENS,
            tools=[
                {
                    "type": "function",
                    "function": {
                        "name": _TOOL["name"],
                        "description": _TOOL["description"],
                        "parameters": _TOOL["input_schema"],
                    },
                }
            ],
            tool_choice={
                "type": "function",
                "function": {"name": "record_changes"},
            },
            messages=[
                {
                    "role": "user",
                    "content": _build_prompt(old_text, new_text, feedback),
                }
            ],
        )
        call = response.choices[0].message.tool_calls
        if not call or call[0].type != "function":
            raise ValueError("OpenAI responded without calling record_changes")
        arguments = json.loads(call[0].function.arguments)
        return _ToolResponse.model_validate(arguments).changes


def build_client(
    *,
    provider: Literal["anthropic", "openai"],
    anthropic_api_key: str | None,
    anthropic_model: str | None,
    openai_api_key: str | None,
    openai_model: str | None,
) -> LLMClient:
    """Builds the chosen provider's client, or raises if its key is missing."""
    if provider == "anthropic":
        if not anthropic_api_key:
            raise ValueError("SEC_FILINGS_AGENT_ANTHROPIC_API_KEY not set")
        if anthropic_model:
            return AnthropicClient(api_key=anthropic_api_key, model=anthropic_model)
        return AnthropicClient(api_key=anthropic_api_key)
    if not openai_api_key:
        raise ValueError("SEC_FILINGS_AGENT_OPENAI_API_KEY not set")
    if openai_model:
        return OpenAIClient(api_key=openai_api_key, model=openai_model)
    return OpenAIClient(api_key=openai_api_key)


def _build_prompt(old_text: str, new_text: str, feedback: list[str]) -> str:
    parts = [
        "Compare the two versions below of the 'Item 1A Risk Factors' "
        "section of a 10-K from the same company, in different years. List "
        "every risk that was added, removed, or meaningfully changed — "
        "ignore purely wording changes with no content change.\n\n"
        "For each change, copy a short passage (one sentence) EXACTLY as it "
        "appears in the corresponding source text — the citation will be "
        "checked by literal match against the original text, so don't "
        "paraphrase.\n\n",
        f"OLD FILING:\n{old_text}\n\n",
        f"NEW FILING:\n{new_text}\n",
    ]
    if feedback:
        parts.append(
            "\n\nIn the previous attempt, these citations weren't found "
            "literally in the source text — fix them, copying the exact "
            "text this time:\n" + "\n".join(f"- {item}" for item in feedback)
        )
    return "".join(parts)
