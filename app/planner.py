import json

from .config import client
from .prompts import PLANNER_INSTRUCTIONS
from .schemas import ImplementationPlan,ToolResult

from tools import (
    list_files,
    list_files_tool_json,
    read_file,
    read_file_tool_json,
)


MAX_PLANNER_TOOL_ITERATIONS = 10


PLANNER_TOOLS = [
    list_files_tool_json,
    read_file_tool_json,
]


def execute_planner_tool(item):
    try:
        arguments = json.loads(item.arguments)

        print("\nPLANNER TOOL:", item.name)
        print("ARGUMENTS:", arguments)

        if item.name == "list_files":
            return list_files(**arguments)

        elif item.name == "read_file":
            return read_file(**arguments)

        raise ValueError(f"Unknown planner tool: {item.name}")

    except Exception as e:
        print(f"Planner tool error: {str(e)}")
        return ToolResult(
            success=False,
            output = "",
            error=f"Tool execution failed: {str(e)}",
        )


def send_planner_tool_outputs(response):
    tool_outputs = []

    for item in response.output:
        if item.type == "function_call":
            result = execute_planner_tool(item)

            tool_outputs.append({
                "type": "function_call_output",
                "call_id": item.call_id,
                "output": result.model_dump_json(),
            })

    return tool_outputs


def create_plan(requirement: str) -> ImplementationPlan:

    response = client.responses.create(
        model="gpt-5.4-nano",
        instructions=PLANNER_INSTRUCTIONS,
        input=requirement,
        tools=PLANNER_TOOLS,
    )

    planner_tool_iterations = 0

    while True:

        tool_outputs = send_planner_tool_outputs(response)

        if not tool_outputs:
            break

        planner_tool_iterations += 1

        print(
            f"\nPLANNER TOOL ITERATION "
            f"{planner_tool_iterations}/"
            f"{MAX_PLANNER_TOOL_ITERATIONS}"
        )

        if planner_tool_iterations >= MAX_PLANNER_TOOL_ITERATIONS:
            raise RuntimeError(
                "Planner reached the maximum number "
                "of tool iterations."
            )

        response = client.responses.create(
            model="gpt-5.4-nano",
            instructions=PLANNER_INSTRUCTIONS,
            previous_response_id=response.id,
            input=tool_outputs,
            tools=PLANNER_TOOLS,
        )

    final_response = client.responses.parse(
        model="gpt-5.4-nano",
        instructions=PLANNER_INSTRUCTIONS,
        previous_response_id=response.id,
        input=[
            {
                "role": "user",
                "content": (
                    "Repository inspection is complete. "
                    "Now return the final structured "
                    "implementation plan based only on "
                    "the repository information you "
                    "actually inspected."
                ),
            }
        ],
        text_format=ImplementationPlan,
    )

    return final_response.output_parsed