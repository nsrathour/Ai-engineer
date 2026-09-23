from .state import AgentState

from app.planner import create_plan

from app.executor import (
    create_executor_response,
    send_tool_outputs,
    continue_executor,
    finalize_executor_response,
)

from app.verifier import run_trusted_verification


def planner_node(state: AgentState):
    plan = create_plan(state["requirement"])

    return {
        "plan": plan
    }


def executor_node(state: AgentState):
    response = create_executor_response(
        state["requirement"],
        state["plan"]
    )

    while True:
        tool_outputs = send_tool_outputs(response)

        if not tool_outputs:
            break

        response = continue_executor(
            response,
            tool_outputs
        )

    executor_result = finalize_executor_response(response)

    return {
        "executor_result": executor_result
    }


def verifier_node(state: AgentState):
    command = state["plan"].verification.command

    result = run_trusted_verification(command)

    passed = result["exit_code"] == 0

    return {
        "verification_command": command,
        "verification_result": result,
        "verification_passed": passed,
        "verification_attempts": state["verification_attempts"] + 1,
    }

def verification_router(state: AgentState):
    if state["verification_passed"]:
        return "end"

    if state["verification_attempts"] >= 3:
        return "end"

    return "retry"