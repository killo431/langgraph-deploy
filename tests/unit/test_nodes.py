import pytest
from langchain_core.messages import HumanMessage

from graphs.nodes import execution_node, router_node


@pytest.mark.parametrize(
    ("messages", "requires_approval"),
    [
        ([HumanMessage(content="This is a CRITICAL operation")], True),
        ([HumanMessage(content="Ordinary task")], False),
        ([HumanMessage(content=[{"type": "text", "text": "critical"}])], True),
        ([], False),
    ],
)
def test_router_node(messages, requires_approval):
    output = router_node({"messages": messages})
    assert output["requires_approval"] is requires_approval
    assert output["approved"] is not requires_approval
    assert len(output["artifacts"]) == 1


def test_execution_node():
    output = execution_node({"artifacts": ["prior_artifact"]})
    assert "successfully" in output["messages"][0].content
    assert output["artifacts"] == ["Task step executed"]
