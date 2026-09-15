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


MAX_VERIFICATION_ATTEMPTS = 3


def run_agent(requirement: str):

    # ---------------------------------------------------------
    # 1. Create implementation plan
    # ---------------------------------------------------------

    plan = create_plan(requirement)

    print("\nPLAN:")
    print(plan)

    success_condition = plan.verification.success_condition

    # ---------------------------------------------------------
    # 2. Start executor
    # ---------------------------------------------------------

    response = create_executor_response(
        requirement,
        plan,
    )

    verification_attempts = 0

    # ---------------------------------------------------------
    # 3. Executor <-> tools loop
    # ---------------------------------------------------------

    while True:

        tool_outputs = send_tool_outputs(response)

        if tool_outputs:
            response = continue_executor(
                response,
                tool_outputs,
            )
            continue

        # -----------------------------------------------------
        # 4. Executor believes implementation is complete
        # -----------------------------------------------------

        print("\nEXECUTOR:")
        print(response.output_text)

        # -----------------------------------------------------
        # 5. Get structured result from executor
        # -----------------------------------------------------

        executor_result = finalize_executor_response(response)

        print("\nEXECUTOR RESULT:")
        print(executor_result)

        if executor_result.status != "completed":
            print("\nEXECUTOR DID NOT COMPLETE")
            print("Stopping the agent.")
            break

        verification_command = (
            executor_result.verification_command.strip()
        )

        if not verification_command:
            print("\nNO VERIFICATION COMMAND")
            print("Stopping the agent.")
            break

        print("\nTRUSTED VERIFICATION COMMAND:")
        print(verification_command)

        # -----------------------------------------------------
        # 6. Trusted verification
        # -----------------------------------------------------

        verification_attempts += 1

        print(
            f"\nVERIFICATION ATTEMPT "
            f"{verification_attempts}/{MAX_VERIFICATION_ATTEMPTS}"
        )

        verification_result = run_trusted_verification(
            verification_command
        )

        verification_passed = verify_result(
            verification_result,
            success_condition,
        )

        # -----------------------------------------------------
        # 7. Verification passed
        # -----------------------------------------------------

        if verification_passed:
            print("\nVERIFICATION PASSED")
            print("Requirement successfully verified.")
            break

        # -----------------------------------------------------
        # 8. Verification environment problem
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
            break

        # -----------------------------------------------------
        # 9. Maximum attempts reached
        # -----------------------------------------------------

        if verification_attempts >= MAX_VERIFICATION_ATTEMPTS:
            print("\nVERIFICATION FAILED")
            print(
                f"Maximum verification attempts "
                f"({MAX_VERIFICATION_ATTEMPTS}) reached."
            )
            print("Stopping the agent.")
            break

        # -----------------------------------------------------
        # 10. Genuine implementation failure
        # -----------------------------------------------------

        print("\nVERIFICATION FAILED")
        print("Sending failure back to executor...")

        response = send_verification_failure(
            response,
            verification_result,
        )