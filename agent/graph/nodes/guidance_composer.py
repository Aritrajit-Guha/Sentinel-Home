# Phase 5: RAG (NDMA docs) + Maps API (shelter/route) -> LLM composes one grounded message
from agent.rag.retriever import retrieve_guidance
from agent.tools.maps_tool import find_nearest_shelter

def guidance_composer(state):
    guidance_docs = retrieve_guidance(state["household_id"])
    shelter, route = find_nearest_shelter(state["household_id"])
    # TODO: call LLM with guidance_docs + shelter + route to compose message
    state["guidance_message"] = "TODO: composed message"
    return state
