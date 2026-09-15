from pydantic import BaseModel


class Verification(BaseModel):
    command: str
    success_condition: str


class ImplementationPlan(BaseModel):
    requirement: str
    plan: list[str]
    files: list[str]
    risks: list[str]
    verification: Verification


class ExecutorResult(BaseModel):
    status: str
    verification_command: str