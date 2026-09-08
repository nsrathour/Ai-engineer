from pathlib import Path


IGNORED_DIRECTORIES = {
    ".venv",
    ".git",
    "__pycache__",
}


def list_files(path: str) -> list[str]:
    directory = Path(path)

    return [
        str(file.relative_to(directory))
        for file in directory.rglob("*")
        if file.is_file()
        and not any(part in IGNORED_DIRECTORIES for part in file.relative_to(directory).parts)
    ]

def read_file(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")

list_files_tool_json = {
    "type": "function",
    "name": "list_files",
    "description": "List all files in the specified project directory.",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "The project directory to inspect."
            }
        },
        "required": ["path"],
        "additionalProperties": False
    }
}

read_file_tool_json = {
    "type": "function",
    "name": "read_file",
    "description": "Read the contents of a file in the project.",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "The path of the file to read."
            }
        },
        "required": ["path"],
        "additionalProperties": False
    }
}