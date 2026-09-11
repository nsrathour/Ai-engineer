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


class ImplementationPlan(BaseModel):
    requirement: str
    plan: list[str]
    files: list[str]
    risks: list[str]
    testing: list[str]


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
        5. Provide a testing strategy.
        6. You do not have access to the user's actual codebase.
        7. Never claim that a specific file, framework, architecture, or dependency already exists.
        8. Clearly treat assumptions as assumptions.
        9. Prefer practical and actionable recommendations over generic explanations.
        """,
        input=requirement,
        text_format=ImplementationPlan,
        # tools=[list_files_tool_json]
    )

    return response.output_parsed

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
        print(f"""gets an error and send back to llm {str(e)}""")
        return f"Tool execution failed: {str(e)}"

def test_tool_calling(requirement, plan):
    response = client.responses.create(
        model="gpt-5.4-nano",
        instructions="""
        You are an AI software engineer.
        Use the available tools when you need information about the project.
        """,
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
            run_command_tool_json
        ]
    )

    while True:
        tool_outputs = []

        for item in response.output:
            if item.type == "function_call":
                result = execute_tool(item)

                tool_outputs.append(
                    {
                        "type": "function_call_output",
                        "call_id": item.call_id,
                        "output": json.dumps(result)
                    }
                )

        if not tool_outputs:
            print(response.output_text)
            break

        response = client.responses.create(
            model="gpt-5.4-nano",
            instructions="""
            You are an AI software engineer.
            Answer the user's request using the available information.
            Use another tool if you need more information.
            """,
            previous_response_id=response.id,
            input=tool_outputs,
            tools=[
                list_files_tool_json,
                read_file_tool_json,
                write_file_tool_json,
                apply_patch_tool_json,
                run_command_tool_json
            ]
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
