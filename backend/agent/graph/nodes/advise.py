"""Advise node: turn a completed risk assessment into a personalized,
RAG-grounded safety message for one household.

This is written as a plain, directly-callable function (matching the style
of scoring_service.assess_household_risk and
model_parameter_tool.generate_parameters_for_household), not a LangGraph
node bound to a StateGraph -- build_graph.py and state.py are still
placeholders, so there's no agreed state schema to bind to yet. Once that
schema exists, wrapping this as a graph node is a thin adapter, not a
rewrite: a node just needs to call generate_advice_for_household with the
right keys pulled out of the graph state and put the result back in.

Expected call site: after app.services.scoring_service.assess_household_risk
has produced an assessment for a household/earthquake pair.
"""

from __future__ import annotations

from agent.graph.state import SentinelState, append_error


NO_GUIDANCE_FOUND = "No relevant safety guidance was found."

# Shown when retrieval comes back empty. Deliberately generic and does not
# invent specific actions -- see the safety note in guidance_prompt.py and
# the module docstring above: an LLM must never be asked to write life-safety
# instructions with no retrieved source to ground them in.
FALLBACK_MESSAGE = (
    "We could not retrieve specific safety guidance for your situation right "
    "now. Please follow instructions from local authorities and emergency "
    "services."
)


def generate_advice_for_household(
    household: dict,
    earthquake: dict,
    assessment: dict,
    *,
    hazard: str = "earthquake",
    k: int = 4,
) -> dict:
    """Retrieve official guidance and turn it into one household's message.

    Returns a dict with the final `message` plus `sources` (the retrieved
    chunks' metadata) and the `query` used, so the result stays auditable --
    an operator can see exactly which documents a given alert's guidance
    came from, not just trust the LLM's output blindly.
    """

    if not isinstance(household, dict) or not isinstance(earthquake, dict) or not isinstance(assessment, dict):
        raise TypeError("household, earthquake, and assessment must all be dicts")

    from agent.prompts.guidance_prompt import build_guidance_prompt, build_retrieval_query
    from agent.rag.retriever import build_context, retrieve_guidance
    from agent.tools.llm_client import generate_guidance_text

    query = build_retrieval_query(earthquake, assessment)
    documents = retrieve_guidance(query, hazard=hazard, k=k)
    context = build_context(documents)

    if not documents or context.strip() == NO_GUIDANCE_FOUND:
        return {
            "message": FALLBACK_MESSAGE,
            "sources": [],
            "query": query,
            "grounded": False,
        }

    prompt = build_guidance_prompt(
        household=household,
        earthquake=earthquake,
        assessment=assessment,
        context=context,
    )
    message = generate_guidance_text(prompt)

    sources = [
        {
            "source": document.metadata.get("source", "unknown source"),
            "page": document.metadata.get("page", "unknown page"),
            "hazard": document.metadata.get("hazard", "general"),
        }
        for document in documents
    ]

    return {
        "message": message,
        "sources": sources,
        "query": query,
        "grounded": True,
    }


def advise_node(state: SentinelState) -> SentinelState:
    """LangGraph adapter around the existing RAG-grounded advice service."""

    household = state.get("household")
    earthquake = state.get("earthquake")
    assessment = state.get("assessment")
    if not all(isinstance(value, dict) for value in (household, earthquake, assessment)):
        return append_error(state, "household, earthquake, and assessment are required for advice")

    try:
        advice = generate_advice_for_household(household, earthquake, assessment)
    except Exception as exc:
        return append_error(state, f"advice generation failed: {exc}")
    return {**state, "advice": advice}
