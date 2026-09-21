from pydantic import BaseModel


class Verification(BaseModel):
    command: str
    success_condition: str


class ImplementationPlan(BaseModel):
    requirement: str
    status: str
    plan: list[str]
    files: list[str]
    risks: list[str]
    verification: Verification

class ExecutorResult(BaseModel):
    status: str
    message: str
    verification_command: str


class ToolResult(BaseModel):
    success: bool
    output: str
    error: str | None = None