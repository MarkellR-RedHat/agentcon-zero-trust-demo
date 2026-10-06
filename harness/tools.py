"""Tool definitions, per stage, in OpenAI function-calling format.

These are the tools the agent is offered. In the demo they are backed by the in-process
sandbox (sandbox_fs.py); on the work laptop the same names are served by an MCP server
(sandbox/Containerfile runs it) over streamable HTTP, and the agent loop does not know the
difference. Stage N offers the tools of every stage up to and including N.
"""

from __future__ import annotations

TOOL_DEFS: dict[str, dict] = {
    "read_file": {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a file from the deploy box and return its contents.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        },
    },
    "write_file": {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Write content to a file on the deploy box.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
                "required": ["path", "content"],
            },
        },
    },
    "list_directory": {
        "type": "function",
        "function": {
            "name": "list_directory",
            "description": "List the files under a directory.",
            "parameters": {
                "type": "object",
                "properties": {"path": {"type": "string"}},
                "required": ["path"],
            },
        },
    },
    "http_get": {
        "type": "function",
        "function": {
            "name": "http_get",
            "description": "Fetch a URL with an HTTP GET and return the body.",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string"}},
                "required": ["url"],
            },
        },
    },
    "http_post": {
        "type": "function",
        "function": {
            "name": "http_post",
            "description": "Send an HTTP POST with a body to a URL.",
            "parameters": {
                "type": "object",
                "properties": {"url": {"type": "string"}, "body": {"type": "string"}},
                "required": ["url"],
            },
        },
    },
    "execute_code": {
        "type": "function",
        "function": {
            "name": "execute_code",
            "description": "Run a snippet of code on the deploy box and return its output.",
            "parameters": {
                "type": "object",
                "properties": {
                    "language": {"type": "string"},
                    "code": {"type": "string"},
                },
                "required": ["code"],
            },
        },
    },
    "run_shell": {
        "type": "function",
        "function": {
            "name": "run_shell",
            "description": "Run a shell command on the deploy box and return its output.",
            "parameters": {
                "type": "object",
                "properties": {"command": {"type": "string"}},
                "required": ["command"],
            },
        },
    },
}

STAGE_TOOLS: dict[int, list[str]] = {
    0: [],
    1: ["read_file", "write_file", "list_directory"],
    2: ["read_file", "write_file", "list_directory", "http_get", "http_post"],
    3: ["read_file", "write_file", "list_directory", "http_get", "http_post",
        "execute_code", "run_shell"],
    4: ["read_file", "list_directory", "write_file"],  # forensic: read the logs, write the report
}


def tools_for_stage(stage: int) -> list[dict]:
    return [TOOL_DEFS[name] for name in STAGE_TOOLS.get(stage, [])]
