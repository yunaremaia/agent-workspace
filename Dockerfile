FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update \
    && apt-get install --no-install-recommends -y ca-certificates git openssh-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /workspace

COPY pyproject.toml README.md LICENSE ./
COPY agent_workspace ./agent_workspace

RUN pip install --no-cache-dir .

ENTRYPOINT ["agent-workspace"]
CMD ["--help"]
