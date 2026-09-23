from .workflow import workflow


initial_state = {
    "requirement": "test my test_agent.py file",
    "plan": None,
    "executor_result": None,
    "verification_command": None,
    "verification_result": None,
    "verification_passed": False,
    "verification_attempts": 0,
    "status": "running",
    "message": "",
}


result = workflow.invoke(initial_state)

print(result)