# ADR-001: Standalone runtime topology

Status: Accepted

## Context
Enterprise deployment requires durable conversational state, resumable human
approval, streaming, reproducible releases, and a clearly separated data plane.

## Decision
- Run LangGraph Standalone Agent Server on Python 3.12 using its Wolfi minimal
  base image, built through the official LangGraph CLI configuration.
- Use Pregel Bulk Synchronous Parallel execution. Shared state channels use
  `Annotated` reducers: `add_messages` for messages, append for artifacts, and
  dictionary merge for context. Parallel context writers must use disjoint keys.
  Approval flags use replacement reducers and have strictly sequential writers;
  they must never be written by parallel branches.
- Dedicate PostgreSQL 16 to assistants, runs, threads, checkpoints, and durable
  queue state. Persist its volume and back it up independently of containers.
- Dedicate Redis 7 to queue coordination and real-time pub/sub message feeds.
- Use `langgraph.types.interrupt` and `Command(resume=...)` for approvals.
  Agent Server supplies the production checkpointer; only tests use an in-memory
  saver. Nodes preceding an interrupt must be replay-safe.
- Register the separate `bmad_project` graph for model-backed IT project planning.
  It emits structured requirements, architecture, backlog, implementation, and
  QA artifacts; architecture requires an explicit human approval and has a bounded
  revision loop. It does not execute generated plans or perform external side
  effects. Project content is sent to the configured model provider and may enter
  LangSmith traces, so data handling must be reviewed before use.
- Keep PostgreSQL and Redis private on the Compose network. Bind the API to
  loopback by default; require an authenticated TLS gateway before remote access.
- Build and smoke-test before publishing lowercase GHCR image names, immutable
  commit tags, and provenance attestations. Never publish pull-request images.

## Consequences
Workers can scale horizontally using the shared services and Agent Server's
thread/run coordination, rather than independently managing checkpoints.
Reducers prevent parallel step write conflicts (`InvalidUpdateError`) without
making conflicting application-level writes safe. Serialize runs per thread.
The included single-host stack does not provide infrastructure high availability.
Production operation needs licensing/credentials, gateway authorization, tested
backups/restores, monitoring, and capacity planning.

## References
- https://github.com/langchain-samples/cicd-pipeline-example
- https://docs.langchain.com/langgraph-platform/cli
- https://docs.langchain.com/langsmith/deploy-standalone-server
- https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry
