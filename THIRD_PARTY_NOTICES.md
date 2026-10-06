# Third-party notices

## Red Hat fonts (Red Hat Display, Red Hat Text, Red Hat Mono)

Bundled in `static/fonts/`, used by the slides, the presenter, and the static demo so they render
offline. Licensed under the SIL Open Font License, Version 1.1. The full license text is in
`static/fonts/OFL.txt`.

## Python dependencies

FastAPI, Uvicorn, Jinja2, pydantic-settings, httpx (app and harness); pytest, ruff (dev);
mcp, mlflow (optional, live runs only). Each under its own license (MIT, BSD, or Apache 2.0);
see each project.

## Models referenced

Qwen3.8-27B is served through vLLM in live runs. It is not redistributed in this repository; it is
pulled from its own source under its own license (Apache 2.0 per its model card).

## Incident account

The stage-4 narrative summarizes public reporting on the July 2026 Hugging Face security incident.
Sources are cited on the slide and in the app: the Hugging Face disclosure
(huggingface.co/blog/security-incident-july-2026) and OpenAI's statement
(openai.com/index/hugging-face-model-evaluation-security-incident).
