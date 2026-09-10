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

def write_file(path: str, content: str) -> str:
    Path(path).write_text(content, encoding="utf-8")
    return f"Successfully wrote to {path}"

def apply_patch(path: str, old_text: str, new_text: str) -> str:
    file = Path(path)

    content = file.read_text(encoding="utf-8")

    if old_text not in content:
        raise ValueError("old_text not found in file")

    updated_content = content.replace(old_text, new_text, 1)

    file.write_text(updated_content, encoding="utf-8")

    return f"Successfully updated {path}"

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

write_file_tool_json = {
    "type": "function",
    "name": "write_file",
    "description": "Write content to a file in the project.",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "The path of the file to write."
            },
            "content": {
                "type": "string",
                "description": "The complete content to write to the file."
            }
        },
        "required": ["path", "content"],
        "additionalProperties": False
    }
}

apply_patch_tool_json = {
    "type": "function",
    "name": "apply_patch",
    "description": "Replace a specific piece of text in an existing file.",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "The path of the file to modify."
            },
            "old_text": {
                "type": "string",
                "description": "The exact text that should be replaced."
            },
            "new_text": {
                "type": "string",
                "description": "The new text that should replace the old text."
            }
        },
        "required": ["path", "old_text", "new_text"],
        "additionalProperties": False
    }
}

