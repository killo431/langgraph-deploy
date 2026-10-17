import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command
from pydantic import ValidationError

from graphs import bmad_workflow


def artifact_fixtures():
    return {
        bmad_workflow.ProjectRequirements: {
            "summary": "Modernize the service desk",
            "in_scope": ["Ticket intake"],
            "out_of_scope": ["Replacing HR systems"],
            "functional_requirements": ["Users can submit tickets"],
            "non_functional_requirements": ["Audit access"],
            "acceptance_criteria": ["A ticket can be tracked"],
            "assumptions": ["Identity provider is available"],
            "risks": ["Migration downtime"],
        },
        bmad_workflow.ArchitectureProposal: {
            "overview": "A secured service desk application",
            "components": ["Web application", "Ticket API"],
            "data_flows": ["Users submit tickets to the API"],
            "security_controls": ["Role-based access"],
            "operational_requirements": ["Monitor API health"],
            "decisions_and_tradeoffs": ["Managed database for operations"],
            "open_questions": ["Confirm retention period"],
        },
        bmad_workflow.ProjectBacklog: {
            "stories": [
                {
                    "id": "IT-1",
                    "title": "Submit a ticket",
                    "user_story": "As a user, I can submit a support ticket.",
                    "acceptance_criteria": ["The ticket is assigned an ID"],
                    "dependencies": [],
                }
            ],
            "sequencing_notes": ["Build identity integration first"],
        },
        bmad_workflow.ImplementationPlan: {
            "tasks": ["Implement ticket intake", "Add audit logging"],
            "migration_and_rollback": ["Test restore before migration"],
            "delivery_dependencies": ["Identity provider access"],
        },
        bmad_workflow.QualityPlan: {
            "test_strategy": ["Automated API and access-control tests"],
            "test_cases": ["Reject unauthenticated ticket submission"],
            "security_and_operability_checks": ["Verify audit event retention"],
            "release_criteria": ["All required tests pass"],
            "unresolved_risks": ["Confirm data-retention requirements"],
        },
    }


def mock_model(monkeypatch, *, architecture_calls=None):
    fixtures = artifact_fixtures()

    def generate(schema, _instructions, payload):
        if schema is bmad_workflow.ArchitectureProposal and architecture_calls is not None:
            architecture_calls.append(payload.get("review_feedback"))
        return fixtures[schema]

    monkeypatch.setattr(bmad_workflow, "_generate", generate)


def project_input():
    return {
        "project_name": "Service desk modernization",
        "project_description": "Replace the legacy IT ticket intake application.",
        "goals": ["Improve ticket visibility"],
        "constraints": ["Keep existing identity provider"],
    }


def test_project_brief_validation_rejects_blank_and_oversized_input():
    with pytest.raises(ValidationError):
        bmad_workflow.validate_project(
            {"project_name": "   ", "project_description": "Description"}
        )
    with pytest.raises(ValidationError):
        bmad_workflow.validate_project(
            {"project_name": "Project", "project_description": "x" * 10_001}
        )
    with pytest.raises(ValidationError):
        bmad_workflow.validate_project(
            {
                "project_name": "Project",
                "project_description": "Description",
                "goals": ["x" * 1_001],
            }
        )


def test_approved_workflow_generates_artifacts(monkeypatch):
    mock_model(monkeypatch)
    graph = bmad_workflow.builder.compile(checkpointer=InMemorySaver())
    config = {"configurable": {"thread_id": "approved-project"}}

    paused = graph.invoke(project_input(), config)

    assert paused["workflow_status"] == "awaiting_architecture_approval"
    assert paused["__interrupt__"][0].value["action"] == "architecture_approval_required"
    assert paused["__interrupt__"][0].value["architecture"]["security_controls"]

    result = graph.invoke(Command(resume={"approved": True}), config)

    assert result["workflow_status"] == "planning_complete"
    assert result["backlog"]["stories"][0]["id"] == "IT-1"
    assert result["implementation_plan"]["tasks"]
    assert result["quality_plan"]["release_criteria"]


def test_rejected_architecture_is_revised_with_feedback(monkeypatch):
    architecture_calls = []
    mock_model(monkeypatch, architecture_calls=architecture_calls)
    graph = bmad_workflow.builder.compile(checkpointer=InMemorySaver())
    config = {"configurable": {"thread_id": "revised-project"}}

    paused = graph.invoke(project_input(), config)
    revised = graph.invoke(
        Command(resume={"approved": False, "feedback": "Add a disaster recovery plan."}),
        config,
    )

    assert paused["workflow_status"] == "awaiting_architecture_approval"
    assert revised["workflow_status"] == "awaiting_architecture_approval"
    assert revised["architecture_review_round"] == 2
    assert architecture_calls == [None, "Add a disaster recovery plan."]

    result = graph.invoke(Command(resume={"approved": True}), config)
    assert result["workflow_status"] == "planning_complete"


@pytest.mark.parametrize(
    "decision",
    [False, "yes", {"approved": "true"}, {"approved": None}],
)
def test_non_boolean_approval_denies_and_review_limit_is_bounded(monkeypatch, decision):
    architecture_calls = []
    mock_model(monkeypatch, architecture_calls=architecture_calls)
    graph = bmad_workflow.builder.compile(checkpointer=InMemorySaver())
    config = {"configurable": {"thread_id": f"denied-{str(decision)}"}}

    result = graph.invoke(project_input(), config)
    for _ in range(bmad_workflow.MAX_ARCHITECTURE_REVIEWS):
        assert result.get("__interrupt__")
        result = graph.invoke(Command(resume=decision), config)

    assert result["workflow_status"] == "architecture_rejected"
    assert result["architecture_review_round"] == bmad_workflow.MAX_ARCHITECTURE_REVIEWS
    assert "backlog" not in result
    assert len(architecture_calls) == bmad_workflow.MAX_ARCHITECTURE_REVIEWS
