# The presenter app. Runs in replay mode by default and serves the bundled run data, so it needs
# no GPU, no cluster and no network at the booth.
FROM registry.access.redhat.com/ubi9/python-312:latest

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
COPY templates ./templates
COPY static ./static
COPY runs ./runs
COPY scripts ./scripts

ENV RUNS_DIR=runs/2026-10-06-SYNTHETIC
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
