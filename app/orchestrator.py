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


MAX_TOOL_ITERATIONS = 20
MAX_VERIFICATION_ATTEMPTS = 3


@dataclass
class AgentResult:
    status: str
    message: str
    verification_passed: bool
    verification_attempts: int


def run_agent(requirement: str):
    tool_iterations = 0

    # ---------------------------------------------------------
    # 1. Create implementation plan
    # ---------------------------------------------------------

    plan = create_plan(requirement)

    print("\nPLAN:")
    print(plan)

    verification_attempts = 0

    # ---------------------------------------------------------
    # 2. Handle Planner status
    # ---------------------------------------------------------

    if plan.status == "blocked":
        print("\nPLANNER BLOCKED")
        print("The requested task cannot currently be performed.")

        if plan.risks:
            print("\nREASON:")
            for risk in plan.risks:
                print(f"- {risk}")

        print("Stopping the agent.")

        return AgentResult(
            status="blocked",
            message=(
                "Planner determined that the requested task "
                "cannot currently be performed."
            ),
            verification_passed=False,
            verification_attempts=verification_attempts,
        )

    if plan.status != "ready":
        print("\nINVALID PLANNER STATUS")
        print(f"Status: {plan.status}")
        print("Stopping the agent.")

        return AgentResult(
            status="failed",
            message=f"Unknown planner status: {plan.status}",
            verification_passed=False,
            verification_attempts=verification_attempts,
        )

    # ---------------------------------------------------------
    # 3. Get verification success condition
    # ---------------------------------------------------------

    success_condition = (
        plan.verification.success_condition
    )

    # ---------------------------------------------------------
    # 4. Start executor
    # ---------------------------------------------------------

    response = create_executor_response(
        requirement,
        plan,
    )

    # ---------------------------------------------------------
    # 5. Executor <-> tools loop
    # ---------------------------------------------------------

    while True:

        tool_outputs = send_tool_outputs(response)

        if tool_outputs:

            tool_iterations += 1

            print(
                f"\nTOOL ITERATION "
                f"{tool_iterations}/{MAX_TOOL_ITERATIONS}"
            )

            if tool_iterations >= MAX_TOOL_ITERATIONS:

                print("\nMAXIMUM TOOL ITERATIONS REACHED")
                print("Stopping the agent.")

                return AgentResult(
                    status="tool_iteration_limit",
                    message="Maximum tool iterations reached.",
                    verification_passed=False,
                    verification_attempts=verification_attempts,
                )

            response = continue_executor(
                response,
                tool_outputs,
            )

            continue

        # -----------------------------------------------------
        # 6. Executor believes implementation is complete
        # -----------------------------------------------------

        print("\nEXECUTOR:")
        print(response.output_text)

        # -----------------------------------------------------
        # 7. Get structured result from executor
        # -----------------------------------------------------

        executor_result = finalize_executor_response(response)

        print("\nEXECUTOR RESULT:")
        print(executor_result)

        # -----------------------------------------------------
        # 8. Executor blocked
        # -----------------------------------------------------

        if executor_result.status == "blocked":

            print("\nEXECUTOR BLOCKED")
            print(executor_result.message)
            print("Stopping the agent.")

            return AgentResult(
                status="blocked",
                message=executor_result.message,
                verification_passed=False,
                verification_attempts=verification_attempts,
            )

        # -----------------------------------------------------
        # 9. Executor failed
        # -----------------------------------------------------

        if executor_result.status == "failed":

            print("\nEXECUTOR FAILED")
            print(executor_result.message)
            print("Stopping the agent.")

            return AgentResult(
                status="failed",
                message=executor_result.message,
                verification_passed=False,
                verification_attempts=verification_attempts,
            )

        # -----------------------------------------------------
        # 10. Unknown executor status
        # -----------------------------------------------------

        if executor_result.status != "completed":

            print("\nINVALID EXECUTOR STATUS")
            print(f"Status: {executor_result.status}")
            print("Stopping the agent.")

            return AgentResult(
                status="failed",
                message=(
                    f"Unknown executor status: "
                    f"{executor_result.status}"
                ),
                verification_passed=False,
                verification_attempts=verification_attempts,
            )

        # -----------------------------------------------------
        # 11. Executor completed
        # -----------------------------------------------------

        verification_command = (
            executor_result.verification_command.strip()
        )

        if not verification_command:

            print("\nNO VERIFICATION COMMAND")
            print("Stopping the agent.")

            return AgentResult(
                status="failed",
                message=(
                    "Executor did not provide "
                    "a verification command."
                ),
                verification_passed=False,
                verification_attempts=verification_attempts,
            )

        print("\nTRUSTED VERIFICATION COMMAND:")
        print(verification_command)

        # -----------------------------------------------------
        # 12. Trusted verification
        # -----------------------------------------------------

        verification_attempts += 1

        print(
            f"\nVERIFICATION ATTEMPT "
            f"{verification_attempts}/"
            f"{MAX_VERIFICATION_ATTEMPTS}"
        )

        verification_result = run_trusted_verification(
            verification_command
        )

        verification_passed = verify_result(
            verification_result,
            success_condition,
        )

        # -----------------------------------------------------
        # 13. Verification passed
        # -----------------------------------------------------

        if verification_passed:

            print("\nVERIFICATION PASSED")
            print("Requirement successfully verified.")

            return AgentResult(
                status="success",
                message="Requirement successfully verified.",
                verification_passed=True,
                verification_attempts=verification_attempts,
            )

        # -----------------------------------------------------
        # 14. Verification environment problem
        # -----------------------------------------------------

        if is_verification_environment_failure(
            verification_result
        ):

            print("\nVERIFICATION COULD NOT RUN")

            print(
                "The verification command could not execute "
                "because the verification environment is unavailable."
            )

            print("Stopping the agent.")

            return AgentResult(
                status="verification_environment_error",
                message=(
                    "Verification environment "
                    "was unavailable."
                ),
                verification_passed=False,
                verification_attempts=verification_attempts,
            )

        # -----------------------------------------------------
        # 15. Maximum verification attempts reached
        # -----------------------------------------------------

        if verification_attempts >= MAX_VERIFICATION_ATTEMPTS:

            print("\nVERIFICATION FAILED")

            print(
                f"Maximum verification attempts "
                f"({MAX_VERIFICATION_ATTEMPTS}) reached."
            )

            print("Stopping the agent.")

            return AgentResult(
                status="verification_failed",
                message=(
                    "Maximum verification attempts reached."
                ),
                verification_passed=False,
                verification_attempts=verification_attempts,
            )

        # -----------------------------------------------------
        # 16. Genuine implementation failure
        # -----------------------------------------------------

        print("\nVERIFICATION FAILED")
        print("Sending failure back to executor...")

        response = send_verification_failure(
            response,
            verification_result,
        )