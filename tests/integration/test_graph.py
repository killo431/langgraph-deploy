import pytest
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command

from graphs.agent import builder
from graphs.state import AgentState


def test_multi_turn_and_thread_isolation():
    checkpointer = InMemorySaver()
    graph = builder.compile(checkpointer=checkpointer)
    config = {"configurable": {"thread_id": "conversation"}}
    first = graph.invoke({"messages": [HumanMessage(content="Hello")]}, config)
    assert len(first["messages"]) == 2
    # Recompile against the same store, as a restarted worker would.
    graph = builder.compile(checkpointer=checkpointer)
    second = graph.invoke({"messages": [HumanMessage(content="Next task")]}, config)
    assert len(second["messages"]) == 4
    assert second["artifacts"].count("Task step executed") == 2
    isolated = graph.invoke(
        {"messages": [HumanMessage(content="Separate")]},
        {"configurable": {"thread_id": "other"}},
    )
    assert len(isolated["messages"]) == 2
    assert "__interrupt__" not in second


@pytest.mark.parametrize(
    ("decision", "approved"),
    [(True, True), ({"approved": True}, True), (False, False),
     ({"approved": False}, False), ("yes", False), ({"approved": None}, False)],
)
def test_interrupt_resume_and_denial(decision, approved):
    graph = builder.compile(checkpointer=InMemorySaver())
    config = {"configurable": {"thread_id": "approval"}}
    paused = graph.invoke(
        {"messages": [HumanMessage(content="critical task")], "context_data": {"id": 7}},
        config,
    )
    assert paused["__interrupt__"][0].value["action"] == "human_approval_required"
    assert paused["__interrupt__"][0].value["context"] == {"id": 7}
    assert "Task step executed" not in paused["artifacts"]
    result = graph.invoke(Command(resume=decision), config)
    assert "__interrupt__" not in result
    assert result["approved"] is approved
    assert ("Task step executed" in result["artifacts"]) is approved
    assert len(result["messages"]) == (3 if approved else 2)
    # Each critical turn must request a fresh approval.
    again = graph.invoke({"messages": [HumanMessage(content="critical again")]}, config)
    assert again["__interrupt__"]


def test_parallel_branch_reducers():
    parallel = StateGraph(AgentState)
    parallel.add_node("left", lambda state: {
        "artifacts": ["left"], "messages": [AIMessage(content="left")],
        "context_data": {"left": 1},
    })
    parallel.add_node("right", lambda state: {
        "artifacts": ["right"], "messages": [AIMessage(content="right")],
        "context_data": {"right": 2},
    })
    for branch in ("left", "right"):
        parallel.add_edge(START, branch)
        parallel.add_edge(branch, END)
    result = parallel.compile().invoke({"messages": [HumanMessage(content="Start")]})
    assert sorted(result["artifacts"]) == ["left", "right"]
    assert len(result["messages"]) == 3
    assert result["context_data"] == {"left": 1, "right": 2}
