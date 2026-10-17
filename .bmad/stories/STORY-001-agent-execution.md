# STORY-001: Agent execution

As an operator, I need durable conversational execution with explicit human
approval so that critical work cannot run before review.

## Acceptance criteria
1. **AC-1**: `GET /ok` returns status 200 with `"ok": true` (current Agent
   Server versions also return a `services` object). The deployed `bmad_agent`
   graph is discoverable through `/assistants/search`.
2. **AC-2**: `add_messages` preserves prior turns; threads remain isolated.
   PostgreSQL-backed state survives API container restarts.
3. **AC-3**: Parallel branch outputs append to artifact/message accumulators and
   merge disjoint context keys without step write conflicts.
4. **AC-4**: Critical input pauses at `interrupt()`. `Command(resume=True)` or
   `Command(resume={"approved": True})` permits execution; every other value
   denies execution. A later critical turn requires a new approval.
5. **AC-5**: CI blocks GHCR publication when unit, integration, deployment smoke,
   or persistence-after-restart tests fail. Cleanup runs even on failure.

## Verification
- `tests/unit/test_nodes.py`: input classification and execution outputs.
- `tests/integration/test_graph.py`: reducers, isolation, multi-turn state, and
  interrupt/resume/denial using a test-only checkpointer.
- `tests/deployment/test_smoke.py`: actual Agent Server health, registration,
  streaming, approval, multi-turn persistence, and post-restart state.
