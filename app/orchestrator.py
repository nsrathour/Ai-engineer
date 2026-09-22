from dataclasses import dataclass

from .executor import (
    create_executor_response,
    send_tool_outputs,
    continue_executor,
    send_verification_failure,
    finalize_executor_response,
)

from .planner import create_plan

from .verifier import (
    run_trusted_verification,
    verify_result,
    is_verification_environment_failure,
)

from .schemas import AgentState


MAX_TOOL_ITERATIONS = 20
MAX_VERIFICATION_ATTEMPTS = 3


@dataclass
class AgentResult:
    status: str
    message: str
    verification_passed: bool
    verification_attempts: int


# =============================================================
# 1. PLANNER STAGE
# =============================================================

def plan_agent(state: AgentState) -> bool:

    state.status = "planning"

    state.plan = create_plan(state.requirement)

    print("\nPLAN:")
    print(state.plan)

    state.verification_attempts = 0

    # ---------------------------------------------------------
    # Planner blocked
    # ---------------------------------------------------------

    if state.plan.status == "blocked":

        state.status = "blocked"

        print("\nPLANNER BLOCKED")
        print("The requested task cannot currently be performed.")

        if state.plan.risks:
            print("\nREASON:")

            for risk in state.plan.risks:
                print(f"- {risk}")

        print("Stopping the agent.")

        return False

    # ---------------------------------------------------------
    # Invalid planner status
    # ---------------------------------------------------------

    if state.plan.status != "ready":

        state.status = "failed"

        print("\nINVALID PLANNER STATUS")
        print(f"Status: {state.plan.status}")
        print("Stopping the agent.")

        return False

    return True


# =============================================================
# 2. EXECUTOR STAGE
# =============================================================

def execute_agent(state: AgentState):

    state.status = "executing"

    response = create_executor_response(
        state.requirement,
        state.plan,
    )

    while True:

        tool_outputs = send_tool_outputs(response)

        if tool_outputs:

            state.tool_iterations += 1

            print(
                f"\nTOOL ITERATION "
                f"{state.tool_iterations}/{MAX_TOOL_ITERATIONS}"
            )

            if state.tool_iterations >= MAX_TOOL_ITERATIONS:

                state.status = "failed"

                print("\nMAXIMUM TOOL ITERATIONS REACHED")
                print("Stopping the agent.")

                return None

            response = continue_executor(
                response,
                tool_outputs,
            )

            continue

        # -----------------------------------------------------
        # Executor believes implementation is complete
        # -----------------------------------------------------

        print("\nEXECUTOR:")
        print(response.output_text)

        state.executor_result = finalize_executor_response(
            response
        )

        print("\nEXECUTOR RESULT:")
        print(state.executor_result)

        # -----------------------------------------------------
        # Executor blocked
        # -----------------------------------------------------

        if state.executor_result.status == "blocked":

            state.status = "blocked"

            print("\nEXECUTOR BLOCKED")
            print(state.executor_result.message)
            print("Stopping the agent.")

            return None

        # -----------------------------------------------------
        # Executor failed
        # -----------------------------------------------------

        if state.executor_result.status == "failed":

            state.status = "failed"

            print("\nEXECUTOR FAILED")
            print(state.executor_result.message)
            print("Stopping the agent.")

            return None

        # -----------------------------------------------------
        # Unknown executor status
        # -----------------------------------------------------

        if state.executor_result.status != "completed":

            state.status = "failed"

            print("\nINVALID EXECUTOR STATUS")
            print(f"Status: {state.executor_result.status}")
            print("Stopping the agent.")

            return None

        return response


# =============================================================
# 3. VERIFIER STAGE
# =============================================================

def verify_agent(state: AgentState, response):

    state.status = "verifying"

    verification_command = (
        state.executor_result.verification_command.strip()
    )

    if not verification_command:

        state.status = "failed"

        print("\nNO VERIFICATION COMMAND")
        print("Stopping the agent.")

        return {
            "done": True,
            "result": AgentResult(
                status="failed",
                message=(
                    "Executor did not provide "
                    "a verification command."
                ),
                verification_passed=False,
                verification_attempts=state.verification_attempts,
            ),
        }

    print("\nTRUSTED VERIFICATION COMMAND:")
    print(verification_command)

    # ---------------------------------------------------------
    # Run verification
    # ---------------------------------------------------------

    state.verification_attempts += 1

    print(
        f"\nVERIFICATION ATTEMPT "
        f"{state.verification_attempts}/"
        f"{MAX_VERIFICATION_ATTEMPTS}"
    )

    state.verification_result = run_trusted_verification(
        verification_command
    )

    verification_passed = verify_result(
        state.verification_result,
        state.plan.verification.success_condition,
    )

    # ---------------------------------------------------------
    # Verification passed
    # ---------------------------------------------------------

    if verification_passed:

        state.status = "success"

        print("\nVERIFICATION PASSED")
        print("Requirement successfully verified.")

        return {
            "done": True,
            "result": AgentResult(
                status="success",
                message="Requirement successfully verified.",
                verification_passed=True,
                verification_attempts=state.verification_attempts,
            ),
        }

    # ---------------------------------------------------------
    # Verification environment problem
    # ---------------------------------------------------------

    if is_verification_environment_failure(
        state.verification_result
    ):

        state.status = "failed"

        print("\nVERIFICATION COULD NOT RUN")

        print(
            "The verification command could not execute "
            "because the verification environment is unavailable."
        )

        print("Stopping the agent.")

        return {
            "done": True,
            "result": AgentResult(
                status="verification_environment_error",
                message=(
                    "Verification environment "
                    "was unavailable."
                ),
                verification_passed=False,
                verification_attempts=state.verification_attempts,
            ),
        }

    # ---------------------------------------------------------
    # Maximum verification attempts
    # ---------------------------------------------------------

    if (
        state.verification_attempts
        >= MAX_VERIFICATION_ATTEMPTS
    ):

        state.status = "failed"

        print("\nVERIFICATION FAILED")

        print(
            f"Maximum verification attempts "
            f"({MAX_VERIFICATION_ATTEMPTS}) reached."
        )

        print("Stopping the agent.")

        return {
            "done": True,
            "result": AgentResult(
                status="verification_failed",
                message=(
                    "Maximum verification attempts reached."
                ),
                verification_passed=False,
                verification_attempts=state.verification_attempts,
            ),
        }

    # ---------------------------------------------------------
    # Genuine implementation failure
    # ---------------------------------------------------------

    print("\nVERIFICATION FAILED")
    print("Sending failure back to executor...")

    new_response = send_verification_failure(
        response,
        state.verification_result,
    )

    return {
        "done": False,
        "response": new_response,
    }


# =============================================================
# MAIN ORCHESTRATOR
# =============================================================

def run_agent(requirement: str):

    state = AgentState(
        requirement=requirement
    )

    # ---------------------------------------------------------
    # Planning
    # ---------------------------------------------------------

    if not plan_agent(state):

        if state.status == "blocked":

            return AgentResult(
                status="blocked",
                message=(
                    "Planner determined that the requested task "
                    "cannot currently be performed."
                ),
                verification_passed=False,
                verification_attempts=state.verification_attempts,
            )

        return AgentResult(
            status="failed",
            message=(
                f"Unknown planner status: "
                f"{state.plan.status}"
            ),
            verification_passed=False,
            verification_attempts=state.verification_attempts,
        )

    # ---------------------------------------------------------
    # Execution
    # ---------------------------------------------------------

    response = execute_agent(state)

    if response is None:

        if state.status == "blocked":

            return AgentResult(
                status="blocked",
                message=(
                    state.executor_result.message
                    if state.executor_result
                    else "Executor blocked."
                ),
                verification_passed=False,
                verification_attempts=state.verification_attempts,
            )

        if state.status == "failed":

            return AgentResult(
                status="failed",
                message=(
                    state.executor_result.message
                    if state.executor_result
                    else "Executor failed."
                ),
                verification_passed=False,
                verification_attempts=state.verification_attempts,
            )

    # ---------------------------------------------------------
    # Verification + retry loop
    # ---------------------------------------------------------

    while True:

        verification = verify_agent(
            state,
            response,
        )

        if verification["done"]:

            return verification["result"]

        # -----------------------------------------------------
        # Verification failed.
        # Executor gets another chance.
        # -----------------------------------------------------

        response = verification["response"]

        state.status = "executing"