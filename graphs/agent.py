from typing import Literal

from langgraph.graph import END, START, StateGraph

from graphs.nodes import execution_node, human_approval_node, router_node
from graphs.state import AgentState


def route_input(state: AgentState) -> Literal["human_approval", "executor"]:
    return "human_approval" if state["requires_approval"] else "executor"


def route_approval(state: AgentState) -> Literal["executor", "__end__"]:
    return "executor" if state["approved"] else END


builder = StateGraph(AgentState)
builder.add_node("router", router_node)
builder.add_node("human_approval", human_approval_node)
builder.add_node("executor", execution_node)
builder.add_edge(START, "router")
builder.add_conditional_edges("router", route_input)
builder.add_conditional_edges("human_approval", route_approval)
builder.add_edge("executor", END)

# Agent Server injects its persistent checkpointer; do not use an in-memory one here.
graph = builder.compile()
