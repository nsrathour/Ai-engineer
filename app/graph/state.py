from typing import TypedDict


class AgentState(TypedDict):
    requirement: str              # User's original request
    plan: object | None           # Plan created by planner
    executor_result: object | None  # Result returned by executor
    verification_command: str | None  # Command used for verification
    verification_result: object | None  # Result from verifier
    verification_passed: bool     # Whether verification passed
    verification_attempts: int    # Number of verification attempts
    status: str                    # Current/final agent status
    message: str                   # Human-readable result message