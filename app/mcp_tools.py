MCP_TOOL_DEFINITIONS = {
    "read_file": {
        "name": "read_file",
        "description": "Read the contents of a file at the given path",
        "icon": "file-text",
        "risk_category": "file",
        "parameters": {"path": {"type": "string", "description": "Absolute file path"}},
    },
    "write_file": {
        "name": "write_file",
        "description": "Write content to a file at the given path",
        "icon": "file-plus",
        "risk_category": "file",
        "parameters": {
            "path": {"type": "string", "description": "Absolute file path"},
            "content": {"type": "string", "description": "Content to write"},
        },
    },
    "list_directory": {
        "name": "list_directory",
        "description": "List files and directories at the given path",
        "icon": "folder",
        "risk_category": "file",
        "parameters": {"path": {"type": "string", "description": "Directory path"}},
    },
    "http_get": {
        "name": "http_get",
        "description": "Make an HTTP GET request to the given URL",
        "icon": "globe",
        "risk_category": "web",
        "parameters": {"url": {"type": "string", "description": "Target URL"}},
    },
    "http_post": {
        "name": "http_post",
        "description": "Make an HTTP POST request with a JSON body",
        "icon": "send",
        "risk_category": "web",
        "parameters": {
            "url": {"type": "string", "description": "Target URL"},
            "body": {"type": "object", "description": "JSON request body"},
        },
    },
    "execute_code": {
        "name": "execute_code",
        "description": "Execute code in a sandboxed environment",
        "icon": "code",
        "risk_category": "code",
        "parameters": {
            "language": {"type": "string", "description": "Programming language"},
            "code": {"type": "string", "description": "Code to execute"},
        },
    },
    "run_shell": {
        "name": "run_shell",
        "description": "Run a shell command",
        "icon": "terminal",
        "risk_category": "code",
        "parameters": {"command": {"type": "string", "description": "Shell command"}},
    },
}

STAGE_TOOLS = {
    0: [],
    1: ["read_file", "write_file", "list_directory"],
    2: ["read_file", "write_file", "list_directory", "http_get", "http_post"],
    3: ["read_file", "write_file", "list_directory", "http_get", "http_post", "execute_code", "run_shell"],
    4: [],
}
