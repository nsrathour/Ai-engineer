from langgraph.graph import StateGraph, START, END

from .state import AgentState
from .nodes import planner_node, executor_node, verifier_node, verification_router


graph = StateGraph(AgentState)

graph.add_node("planner", planner_node)
graph.add_node("executor", executor_node)
graph.add_node("verifier", verifier_node)

graph.add_edge(START, "planner")
graph.add_edge("planner", "executor")
graph.add_edge("executor", "verifier")

graph.add_conditional_edges(
    "verifier",
    verification_router,
    {
        "end": END,
        "retry": "executor",
    },
)

workflow = graph.compile()