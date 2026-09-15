import subprocess


def verify_result(result, success_condition):
    if success_condition == "exit_code == 0":
        return result["exit_code"] == 0

    raise ValueError(
        f"Unsupported success condition: {success_condition}"
    )


def run_trusted_verification(command):
    print("\nVERIFICATION:")
    print("COMMAND:", command)

    try:
        completed = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
        )

        result = {
            "command": command,
            "exit_code": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }

        print("EXIT CODE:", completed.returncode)

        if completed.stdout:
            print("STDOUT:")
            print(completed.stdout)

        if completed.stderr:
            print("STDERR:")
            print(completed.stderr)

        return result

    except Exception as e:
        return {
            "command": command,
            "exit_code": -1,
            "stdout": "",
            "stderr": str(e),
        }


def is_verification_environment_failure(result):
    stderr = result["stderr"].lower()

    environment_errors = [
        "is not recognized as an internal or external command",
        "no module named",
        "command not found",
        "not found",
        "no such file or directory",
    ]

    return any(
        error in stderr
        for error in environment_errors
    )