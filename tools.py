from pathlib import Path
import subprocess

from app.schemas import ToolResult


IGNORED_DIRECTORIES = {
    ".venv",
    ".git",
    "__pycache__",
}


def success_result(output: str) -> ToolResult:
    return ToolResult(
        success=True,
        output=output,
        error=None,
    )


def error_result(error: str) -> ToolResult:
    return ToolResult(
        success=False,
        output="",
        error=error,
    )


def list_files(path: str) -> ToolResult:
    try:
        directory = Path(path)

        if not directory.exists():
            return error_result(
                f"Directory not found: {path}"
            )

        if not directory.is_dir():
            return error_result(
                f"Path is not a directory: {path}"
            )

        files = [
            str(file.relative_to(directory))
            for file in directory.rglob("*")
            if file.is_file()
            and not any(
                part in IGNORED_DIRECTORIES
                for part in file.relative_to(directory).parts
            )
        ]

        return success_result(
            "\n".join(files)
        )

    except Exception as e:
        return error_result(
            f"Failed to list files: {e}"
        )


def read_file(path: str) -> ToolResult:
    try:
        file = Path(path)

        if not file.exists():
            return error_result(
                f"File not found: {path}"
            )

        if not file.is_file():
            return error_result(
                f"Path is not a file: {path}"
            )

        content = file.read_text(
            encoding="utf-8"
        )

        return success_result(content)

    except UnicodeDecodeError:
        return error_result(
            f"File is not valid UTF-8 text: {path}"
        )

    except Exception as e:
        return error_result(
            f"Failed to read file {path}: {e}"
        )


def write_file(
    path: str,
    content: str,
) -> ToolResult:
    try:
        file = Path(path)

        file.write_text(
            content,
            encoding="utf-8",
        )

        return success_result(
            f"Successfully wrote to {path}"
        )

    except Exception as e:
        return error_result(
            f"Failed to write file {path}: {e}"
        )


def apply_patch(
    path: str,
    old_text: str,
    new_text: str,
) -> ToolResult:
    try:
        file = Path(path)

        if not file.exists():
            return error_result(
                f"File not found: {path}"
            )

        if not file.is_file():
            return error_result(
                f"Path is not a file: {path}"
            )

        content = file.read_text(
            encoding="utf-8"
        )

        if old_text not in content:
            return error_result(
                f"old_text not found in file: {path}"
            )

        updated_content = content.replace(
            old_text,
            new_text,
            1,
        )

        file.write_text(
            updated_content,
            encoding="utf-8",
        )

        return success_result(
            f"Successfully updated {path}"
        )

    except UnicodeDecodeError:
        return error_result(
            f"File is not valid UTF-8 text: {path}"
        )

    except Exception as e:
        return error_result(
            f"Failed to apply patch to {path}: {e}"
        )


def run_command(command: str) -> ToolResult:
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
        )

        output = (
            f"exit_code: {result.returncode}\n"
            f"stdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )

        return success_result(output)

    except Exception as e:
        return error_result(
            f"Failed to run command: {e}"
        )


# ---------------------------------------------------------
# Tool JSON Schemas
# ---------------------------------------------------------

list_files_tool_json = {
    "type": "function",
    "name": "list_files",
    "description": (
        "List all files in a directory recursively while "
        "ignoring common generated and environment directories."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Directory path to inspect.",
            }
        },
        "required": ["path"],
        "additionalProperties": False,
    },
}


read_file_tool_json = {
    "type": "function",
    "name": "read_file",
    "description": "Read the contents of a text file.",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path of the file to read.",
            }
        },
        "required": ["path"],
        "additionalProperties": False,
    },
}


write_file_tool_json = {
    "type": "function",
    "name": "write_file",
    "description": "Create or overwrite a text file.",
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path of the file to write.",
            },
            "content": {
                "type": "string",
                "description": "Content to write to the file.",
            },
        },
        "required": ["path", "content"],
        "additionalProperties": False,
    },
}


apply_patch_tool_json = {
    "type": "function",
    "name": "apply_patch",
    "description": (
        "Replace the first occurrence of old_text in a file "
        "with new_text."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Path of the file to modify.",
            },
            "old_text": {
                "type": "string",
                "description": "Existing text to replace.",
            },
            "new_text": {
                "type": "string",
                "description": "Replacement text.",
            },
        },
        "required": [
            "path",
            "old_text",
            "new_text",
        ],
        "additionalProperties": False,
    },
}


run_command_tool_json = {
    "type": "function",
    "name": "run_command",
    "description": (
        "Execute a shell command and return its exit code, "
        "stdout, and stderr."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "Shell command to execute.",
            }
        },
        "required": ["command"],
        "additionalProperties": False,
    },
}