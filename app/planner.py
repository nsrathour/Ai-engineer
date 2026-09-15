from .config import client
from .prompts import PLANNER_INSTRUCTIONS
from .schemas import ImplementationPlan


def create_plan(requirement: str) -> ImplementationPlan:
    response = client.responses.parse(
        model="gpt-5.4-nano",
        instructions=PLANNER_INSTRUCTIONS,
        input=requirement,
        text_format=ImplementationPlan,
    )

    return response.output_parsed