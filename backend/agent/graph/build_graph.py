"""Build and run the SentinelHome LangGraph workflow."""

from __future__ import annotations

from functools import lru_cache

from langgraph.graph import END, START, StateGraph

from agent.graph.nodes.alert import alert_node
from agent.graph.nodes.advise import advise_node
from agent.graph.nodes.assess import assess_node
from agent.graph.nodes.end_silent import end_silent_node
from agent.graph.nodes.escalate import escalate_node
from agent.graph.nodes.observe import observe_node
from agent.graph.state import SentinelState


def _after_assess(state: SentinelState) -> str:
    if state.get("errors"):
        return "end"
    return "silent" if state.get("silent") else "advise"


def _after_alert(state: SentinelState) -> str:
    return "end" if state.get("errors") else "observe"


def _after_observe(state: SentinelState) -> str:
    return "escalate" if state.get("escalation_required") else "end"


@lru_cache(maxsize=1)
def build_graph():
    graph = StateGraph(SentinelState)
    graph.add_node("assess", assess_node)
    graph.add_node("advise", advise_node)
    graph.add_node("alert", alert_node)
    graph.add_node("observe", observe_node)
    graph.add_node("escalate", escalate_node)
    graph.add_node("end_silent", end_silent_node)
    graph.add_edge(START, "assess")
    graph.add_conditional_edges(
        "assess", _after_assess,
        {"silent": "end_silent", "advise": "advise", "end": END},
    )
    graph.add_edge("advise", "alert")
    graph.add_conditional_edges(
        "alert", _after_alert, {"observe": "observe", "end": END}
    )
    graph.add_conditional_edges(
        "observe", _after_observe, {"escalate": "escalate", "end": END}
    )
    graph.add_edge("escalate", END)
    graph.add_edge("end_silent", END)
    return graph.compile()


def run_agent_workflow(household: dict, earthquake: dict, event_callback=None, simulation: bool = False) -> SentinelState:
    return build_graph().invoke({
        "household": household,
        "earthquake": earthquake,
        "errors": [],
        "completed": False,
        "trace": [],
        "_trace_callback": event_callback,
        "simulation": simulation,
    })
