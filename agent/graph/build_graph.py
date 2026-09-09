from langgraph.graph import StateGraph, END
from agent.graph.state import AgentState
from agent.graph.nodes.threshold_check import threshold_check
from agent.graph.nodes.guidance_composer import guidance_composer
from agent.graph.nodes.escalation import escalation
from agent.graph.nodes.reassessment import reassessment

def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("threshold_check", threshold_check)
    graph.add_node("guidance_composer", guidance_composer)
    graph.add_node("escalation", escalation)
    graph.add_node("reassessment", reassessment)

    graph.set_entry_point("threshold_check")
    graph.add_conditional_edges(
        "threshold_check",
        lambda s: "guidance_composer" if s["triggered"] else END,
    )
    graph.add_edge("guidance_composer", "escalation")
    graph.add_edge("escalation", "reassessment")
    graph.add_edge("reassessment", END)

    return graph.compile()
