import json
from pathlib import Path

from .config import client
from .prompts import PLANNER_INSTRUCTIONS
from .schemas import ImplementationPlan, ToolResult

from tools import (
    list_files,
    list_files_tool_json,
    read_file,
    read_file_tool_json,
)


MAX_PLANNER_TOOL_ITERATIONS = 10
MAX_REPEATED_TOOL_CALLS = 3


PLANNER_TOOLS = [
    list_files_tool_json,
    read_file_tool_json,
]


def make_tool_cache_key(item):
    """
    Create a deterministic cache key for a planner tool call.

    Paths such as:
        .
        ./
        ././

    are normalized to the same absolute path.
    """

    arguments = json.loads(item.arguments)

    normalized_arguments = dict(arguments)

    if "path" in normalized_arguments:
        normalized_arguments["path"] = str(
            Path(normalized_arguments["path"]).resolve()
        )

    return (
        item.name,
        json.dumps(
            normalized_arguments,
            sort_keys=True,
            separators=(",", ":"),
        ),
    )


def execute_planner_tool(item, tool_cache):
    """
    Execute a planner tool or return a cached result.
    """

    try:
        cache_key = make_tool_cache_key(item)

        # --------------------------------
        # CACHE HIT
        # --------------------------------
        if cache_key in tool_cache:
            print("\nPLANNER TOOL CACHE HIT")
            print("TOOL:", item.name)
            print(
                "ARGUMENTS:",
                json.loads(item.arguments),
            )

            return tool_cache[cache_key]

        arguments = json.loads(item.arguments)

        print("\nPLANNER TOOL:", item.name)
        print("ARGUMENTS:", arguments)

        # --------------------------------
        # TOOL EXECUTION
        # --------------------------------
        if item.name == "list_files":
            result = list_files(**arguments)

        elif item.name == "read_file":
            result = read_file(**arguments)

        else:
            raise ValueError(
                f"Unknown planner tool: {item.name}"
            )

        # --------------------------------
        # STORE RESULT IN CACHE
        # --------------------------------
        tool_cache[cache_key] = result

        return result

    except Exception as e:
        print(f"Planner tool error: {str(e)}")

        return ToolResult(
            success=False,
            output="",
            error=f"Tool execution failed: {str(e)}",
        )


def send_planner_tool_outputs(
    response,
    tool_cache,
    tool_call_counts,
):
    """
    Execute planner tool calls and return their outputs.

    Every function call produced by the model receives a
    corresponding function_call_output.

    Repeated identical tool calls are limited so that the
    planner cannot waste iterations repeatedly requesting
    the same repository information.
    """

    tool_outputs = []

    for item in response.output:

        if item.type != "function_call":
            continue

        cache_key = make_tool_cache_key(item)

        # --------------------------------
        # COUNT TOOL CALL
        # --------------------------------
        tool_call_counts[cache_key] = (
            tool_call_counts.get(cache_key, 0) + 1
        )

        # --------------------------------
        # REPEATED CALL LIMIT
        # --------------------------------
        if (
            tool_call_counts[cache_key]
            > MAX_REPEATED_TOOL_CALLS
        ):
            print(
                "\nPLANNER REPEATED TOOL CALL "
                "LIMIT REACHED"
            )

            print("TOOL:", item.name)
            print(
                "ARGUMENTS:",
                json.loads(item.arguments),
            )

            result = ToolResult(
                success=False,
                output=(
                    "This tool request has been repeated "
                    "too many times. The repository "
                    "information for this request has "
                    "already been provided. Do not request "
                    "the same information again. Use the "
                    "information already available and "
                    "produce the final implementation plan."
                ),
                error="Repeated tool call limit reached.",
            )

        else:
            result = execute_planner_tool(
                item,
                tool_cache,
            )

        # --------------------------------
        # ALWAYS RETURN TOOL OUTPUT
        # --------------------------------
        tool_outputs.append(
            {
                "type": "function_call_output",
                "call_id": item.call_id,
                "output": result.model_dump_json(),
            }
        )

    return tool_outputs


def create_plan(requirement: str) -> ImplementationPlan:

    # --------------------------------
    # PLANNING-RUN CACHE
    # --------------------------------
    # Cache exists only for this planning request.
    #
    # This prevents stale repository information
    # from being reused between different user requests.
    tool_cache = {}

    # --------------------------------
    # TOOL CALL TRACKING
    # --------------------------------
    tool_call_counts = {}

    # --------------------------------
    # INITIAL PLANNER REQUEST
    # --------------------------------
    response = client.responses.create(
        model="gpt-5.4-nano",
        instructions=PLANNER_INSTRUCTIONS,
        input=requirement,
        tools=PLANNER_TOOLS,
    )

    planner_tool_iterations = 0

    # --------------------------------
    # PLANNER TOOL LOOP
    # --------------------------------
    while True:

        tool_outputs = send_planner_tool_outputs(
            response,
            tool_cache,
            tool_call_counts,
        )

        # --------------------------------
        # NO TOOL CALLS
        # --------------------------------
        # The planner has finished repository inspection
        # and can now produce the final structured plan.
        if not tool_outputs:
            break

        planner_tool_iterations += 1

        print(
            f"\nPLANNER TOOL ITERATION "
            f"{planner_tool_iterations}/"
            f"{MAX_PLANNER_TOOL_ITERATIONS}"
        )

        # --------------------------------
        # MAX ITERATION GUARD
        # --------------------------------
        if (
            planner_tool_iterations
            >= MAX_PLANNER_TOOL_ITERATIONS
        ):
            raise RuntimeError(
                "Planner reached the maximum number "
                "of tool iterations."
            )

        # --------------------------------
        # CONTINUE PLANNER
        # --------------------------------
        response = client.responses.create(
            model="gpt-5.4-nano",
            instructions=PLANNER_INSTRUCTIONS,
            previous_response_id=response.id,
            input=tool_outputs,
            tools=PLANNER_TOOLS,
        )

    # --------------------------------
    # FINAL STRUCTURED PLAN
    # --------------------------------
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