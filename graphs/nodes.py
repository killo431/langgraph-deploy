from typing import Any

from langchain_core.messages import AIMessage
from langgraph.types import interrupt

from graphs.state import AgentState


def router_node(state: AgentState) -> dict[str, Any]:
    messages = state.get("messages", [])
    last_message = str(messages[-1].content) if messages else ""
    needs_approval = "critical" in last_message.lower()
    return {
        "requires_approval": needs_approval,
        "approved": not needs_approval,
        "artifacts": [f"Evaluated input: {last_message[:30]}"],
    }


def human_approval_node(state: AgentState) -> dict[str, Any]:
    decision = interrupt({
        "action": "human_approval_required",
        "reason": "Critical execution requested",
        "context": state.get("context_data", {}),
    })
    approved = decision is True or (
        isinstance(decision, dict) and decision.get("approved") is True
    )
    return {
        "messages": [
            AIMessage(content=f"Human review result: {'approved' if approved else 'rejected'}")
        ],
        "requires_approval": False,
        "approved": approved,
    }


def execution_node(state: AgentState) -> dict[str, Any]:
    return {
        "messages": [
            AIMessage(content="Task executed successfully in accordance with BMAD AC.")
        ],
        "artifacts": ["Task step executed"],
    }
