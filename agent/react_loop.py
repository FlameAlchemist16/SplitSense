from typing import Callable

from agent.agent_tools import AgentToolRunner, TOOL_DEFINITIONS
from agent.llm_client import LLM_MODEL, haiku_client


def run_react_turn(
    *,
    system: str,
    messages: list[dict],
    tool_runner: AgentToolRunner,
    user_input: str | None = None,
    max_tool_rounds: int = 8,
) -> tuple[list[dict], str]:
    """
    One user turn: append user message, run ReAct tool loop until model ends turn.
    Returns updated messages and the final assistant text for display.
    """
    if user_input:
        messages.append({"role": "user", "content": user_input})

    if not LLM_MODEL:
        raise ValueError("LLM_MODEL is not set in .env")

    assistant_text = ""
    for _ in range(max_tool_rounds):
        response = haiku_client.messages.create(
            model=LLM_MODEL,
            max_tokens=4096,
            system=system,
            tools=TOOL_DEFINITIONS,
            messages=messages,
        )
        messages.append({"role": "assistant", "content": response.content})

        if response.stop_reason == "end_turn":
            assistant_text = _text_from_blocks(response.content)
            break

        if response.stop_reason != "tool_use":
            assistant_text = _text_from_blocks(response.content)
            break

        tool_results = []
        for block in response.content:
            if block.type != "tool_use":
                continue
            result = tool_runner.dispatch(block.name, block.input)
            tool_results.append(
                {
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": _serialize_tool_result(result),
                }
            )
        messages.append({"role": "user", "content": tool_results})
    else:
        assistant_text = (
            assistant_text
            or "I hit the tool limit for this turn. Please continue or simplify the request."
        )

    return messages, assistant_text


def _text_from_blocks(blocks) -> str:
    parts = []
    for block in blocks:
        if block.type == "text":
            parts.append(block.text)
    return "\n".join(parts).strip()


def _serialize_tool_result(result) -> str:
    import json

    return json.dumps(result, default=str)
