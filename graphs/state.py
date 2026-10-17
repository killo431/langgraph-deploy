import operator
from typing import Annotated, Any, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


def replace_flag(previous: bool, current: bool) -> bool:
    """Replace flags written only by sequential routing/approval nodes."""
    return current


class AgentState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]
    context_data: Annotated[dict[str, Any], operator.or_]
    artifacts: Annotated[list[str], operator.add]
    requires_approval: Annotated[bool, replace_flag]
    approved: Annotated[bool, replace_flag]
