FROM langchain/langgraph-api:0.16.1-py3.12-wolfi@sha256:7d03f0e4135a87725037fb9a47f0d056c56a6dae354679b09c3ce98c017daed6

WORKDIR /deps/bmad-agent
COPY . /deps/bmad-agent

# Respect both the application's lock and the Agent Server compatibility constraints.
RUN uv export --frozen --no-dev --no-emit-project --no-hashes --output-file /tmp/app-requirements.txt && \
    PYTHONDONTWRITEBYTECODE=1 uv pip install --system --no-cache-dir \
    -c /api/constraints.txt -c /tmp/app-requirements.txt -e . && \
    rm /tmp/app-requirements.txt

ENV LANGGRAPH_HTTP='{"disable_meta": false}'
ENV LANGGRAPH_CHECKPOINTER='{"ttl": {"strategy": "delete", "sweep_interval_minutes": 60, "default_ttl": 43200}}'
ENV LANGSERVE_GRAPHS='{"bmad_agent": "/deps/bmad-agent/graphs/agent.py:graph", "bmad_project": "/deps/bmad-agent/graphs/bmad_workflow.py:graph"}'

# Preserve the server package after installing user dependencies (CLI convention).
RUN mkdir -p /api/langgraph_api /api/langgraph_runtime /api/langgraph_license && \
    touch /api/langgraph_api/__init__.py /api/langgraph_runtime/__init__.py /api/langgraph_license/__init__.py && \
    PYTHONDONTWRITEBYTECODE=1 uv pip install --system --no-cache-dir --no-deps -e /api
