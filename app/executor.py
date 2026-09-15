import json

from .config import client
from .prompts import EXECUTOR_INSTRUCTIONS
from .schemas import ExecutorResult

from tools import (
    list_files,
    list_files_tool_json,
    read_file,
    read_file_tool_json,
    write_file,
    write_file_tool_json,
    apply_patch,
    apply_patch_tool_json,
    run_command,
    run_command_tool_json,
)


TOOLS = [
    list_files_tool_json,
    read_file_tool_json,
    write_file_tool_json,
    apply_patch_tool_json,
    run_command_tool_json,
]


def execute_tool(item):
    try:
        arguments = json.loads(item.arguments)

        print("\nTOOL:", item.name)
        print("ARGUMENTS:", arguments)

        if item.name == "list_files":
            return list_files(**arguments)

        elif item.name == "read_file":
            return read_file(**arguments)

        elif item.name == "write_file":
            return write_file(**arguments)

        elif item.name == "apply_patch":
            return apply_patch(**arguments)

        elif item.name == "run_command":
            return run_command(**arguments)

        raise ValueError(f"Unknown tool: {item.name}")

    except Exception as e:
        print(f"gets an error and send back to llm {str(e)}")
        return f"Tool execution failed: {str(e)}"


def create_executor_response(requirement, plan):
    return client.responses.create(
        model="gpt-5.4-nano",
        instructions=EXECUTOR_INSTRUCTIONS,
        input=f"""
        User requirement:

        {requirement}

        Implementation plan:

        {json.dumps(plan.model_dump(), indent=2)}
        """,
        tools=TOOLS,
    )


def send_tool_outputs(response):
    tool_outputs = []

    for item in response.output:
        if item.type == "function_call":
            result = execute_tool(item)

            tool_outputs.append({
                "type": "function_call_output",
                "call_id": item.call_id,
                "output": json.dumps(result),
            })

    return tool_outputs


def continue_executor(response, tool_outputs):
    return client.responses.create(
        model="gpt-5.4-nano",
        instructions=EXECUTOR_INSTRUCTIONS,
        previous_response_id=response.id,
        input=tool_outputs,
        tools=TOOLS,
    )


def finalize_executor_response(response):
    final_response = client.responses.parse(
        model="gpt-5.4-nano",
        instructions="""
        The implementation phase is complete.

        Based on the work performed in the previous conversation,
        return a structured result for the Python orchestrator.

        Rules:

        1. status must be "completed" if the implementation work is complete.
        2. verification_command must contain the single command that
           the Python orchestrator should execute to verify the work.
        3. Choose the verification command based on the actual codebase
           and the verification requirements.
        4. Do not simply repeat the planner's command if inspection of
           the repository showed that another command is more appropriate.
        5. Do not claim that verification passed.
           The Python orchestrator will run the command independently.
        """,
        previous_response_id=response.id,
        input=[
            {
                "role": "user",
                "content": "Return the final structured executor result.",
            }
        ],
        text_format=ExecutorResult,
    )

    return final_response.output_parsed


def send_verification_failure(response, verification_result):
    return client.responses.create(
        model="gpt-5.4-nano",
        instructions=EXECUTOR_INSTRUCTIONS,
        previous_response_id=response.id,
        input=[{
            "role": "user",
            "content": (
                "The trusted verification performed by the "
                "Python orchestrator failed.\n\n"
                "Verification result:\n"
                f"{json.dumps(verification_result, indent=2)}\n\n"
                "Inspect the failure and determine whether it is "
                "caused by the implementation.\n\n"
                "If it is an implementation problem, fix the "
                "actual implementation.\n\n"
                "Do not modify test files, test runners, "
                "dependencies, or the verification environment "
                "just to make the verification pass.\n\n"
                "When the implementation fix is complete, stop."
            ),
        }],
        tools=TOOLS,
    )