# PRD 001: Core conversational agent

## Objective
Deliver a production-deployable, multi-turn conversational agent with native
human-in-the-loop approvals, managed through BMAD specifications, architecture
decisions, acceptance tests, and gated releases.

## Functional requirements
- Route ordinary input to autonomous execution and critical input to human approval.
- Pause critical execution using `interrupt()`; resume with `Command(resume=...)`.
  Only an explicit boolean approval authorizes execution; denial ends the run.
- Preserve messages and artifacts across turns and server restarts using the
  Agent Server PostgreSQL checkpointer, isolated by thread ID.
- Stream execution events through Agent Server streaming endpoints backed by
  Redis pub/sub. Redis is not the durable source of conversation state.

## Non-functional requirements
- Run continuously on standalone servers without scale-to-zero cold starts.
  Restart policies are not a guarantee of zero downtime during host failure or
  single-instance upgrades; high availability requires redundant infrastructure.
- Collect end-to-end traces in LangSmith with server-side tracing enabled.
  Restrict trace access and review data retention before sending sensitive input.
- Target autonomous response latency below 2.5 seconds at the deployment's
  measured workload, excluding human wait time. Verify under load before rollout;
  the deterministic reference executor performs no remote model calls.

## Scope and safety
The reference executor emits a deterministic acknowledgement rather than invoking
external tools. Replace it with domain-specific, authorized tools only after
extending acceptance tests. Keyword routing demonstrates the approval protocol;
it is not an authorization boundary for sensitive operations.
