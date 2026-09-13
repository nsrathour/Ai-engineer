import json

from openai import OpenAI
from dotenv import load_dotenv
from pydantic import BaseModel

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


load_dotenv()

client = OpenAI()


EXECUTOR_INSTRUCTIONS = """
You are an AI software engineer responsible for implementing the user's requirement.

Use the implementation plan as guidance, but inspect the actual codebase before making changes.

You have access to tools for:

- inspecting files
- reading files
- writing files
- applying patches
- running commands

Follow this workflow:

1. Inspect the relevant code before making changes.
2. Implement the requested change using the appropriate tools.
3. If the requirement involves code changes or testing, verify the implementation by running the relevant tests or commands.
4. Carefully inspect the verification result.
5. If verification fails, diagnose the failure, make the necessary fix, and run the verification again.
6. Continue the fix → verify cycle until the requirement is successfully verified or you determine that it cannot be completed.
7. Only provide the final answer after completing the necessary verification.

Do not claim that a change was made unless you actually made it.

Do not claim that tests passed unless you actually ran them and received a successful result.

Do not stop after a failed verification when the failure can reasonably be fixed.
"""


class Verification(BaseModel):
    command: str
    success_condition: str


class ImplementationPlan(BaseModel):
    requirement: str
    plan: list[str]
    files: list[str]
    risks: list[str]
    verification: Verification


def create_plan(requirement):
    response = client.responses.parse(
        model="gpt-5.4-nano",
        instructions="""
        You are an AI software engineer responsible for analyzing software requirements.

        Your job is to create a practical implementation plan for the user's requirement.

        Follow these rules:

        1. Clearly understand and restate the requirement.
        2. Break the work into logical implementation steps.
        3. Suggest files or areas that are likely to be involved.
        4. Identify important technical risks and edge cases.
        5. Define exactly how the implementation should be verified.
        6. Provide one concrete verification command.
        7. Define the condition that means the verification passed.
        8. You do not have access to the user's actual codebase.
        9. Never claim that a specific file, framework, architecture, or dependency already exists.
        10. Clearly treat assumptions as assumptions.
        11. Prefer practical and actionable recommendations over generic explanations.
        """,
        input=requirement,
        text_format=ImplementationPlan,
        # tools=[list_files_tool_json]
    )

    return response.output_parsed

def verify_result(result, success_condition):
    if success_condition == "exit_code == 0":
        return "exit_code: 0" in str(result)

    raise ValueError(
        f"Unsupported success condition: {success_condition}"
    )

def execute_tool(item):
    try:
        arguments = json.loads(item.arguments)

        print("TOOL:", item.name)
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


def test_tool_calling(requirement, plan):
    verification_done = False
    verification_passed = False

    verification_command = plan.verification.command

    response = client.responses.create(
        model="gpt-5.4-nano",
        instructions=EXECUTOR_INSTRUCTIONS,
        input=f"""
        User requirement:

        {requirement}

        Implementation plan:

        {json.dumps(plan.model_dump(), indent=2)}
        """,
        tools=[
            list_files_tool_json,
            read_file_tool_json,
            write_file_tool_json,
            apply_patch_tool_json,
            run_command_tool_json,
        ],
    )

    while True:
        tool_outputs = []

        for item in response.output:
            if item.type == "function_call":
                result = execute_tool(item)

                if item.name == "run_command":
                    arguments = json.loads(item.arguments)

                    command = arguments.get("command", "")

                    if command == verification_command:
                        verification_done = True

                        if "exit_code: 0" in str(result):
                            verification_passed = True
                        else:
                            verification_passed = False

                tool_outputs.append(
                    {
                        "type": "function_call_output",
                        "call_id": item.call_id,
                        "output": json.dumps(result),
                    }
                )

        if not tool_outputs:

            if verification_done and verification_passed:
                print(response.output_text)
                break

            if verification_done and not verification_passed:
                response = client.responses.create(
                    model="gpt-5.4-nano",
                    instructions=EXECUTOR_INSTRUCTIONS,
                    previous_response_id=response.id,
                    input=[
                        {
                            "role": "user",
                            "content": (
                                "The verification command failed. "
                                "Do not finish yet. "
                                "Inspect the failure, fix the problem, "
                                "and run the verification command again."
                            ),
                        }
                    ],
                    tools=[
                        list_files_tool_json,
                        read_file_tool_json,
                        write_file_tool_json,
                        apply_patch_tool_json,
                        run_command_tool_json,
                    ],
                )

                continue

            print(response.output_text)
            break

        response = client.responses.create(
            model="gpt-5.4-nano",
            instructions=EXECUTOR_INSTRUCTIONS,
            previous_response_id=response.id,
            input=tool_outputs,
            tools=[
                list_files_tool_json,
                read_file_tool_json,
                write_file_tool_json,
                apply_patch_tool_json,
                run_command_tool_json,
            ],
        )


requirement = """
Run the tests in test_agent.py.

If they fail, identify the problem, fix it,
and run the tests again to verify the fix.
"""

plan = create_plan(requirement)

print("PLAN:")
print(plan)

test_tool_calling(requirement, plan)

