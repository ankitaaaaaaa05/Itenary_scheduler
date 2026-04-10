# """
# agents.py — All LangGraph agents + workflow
# """
# import json
# import copy
# from typing import TypedDict, Optional, Annotated
# import operator

# from langgraph.graph import StateGraph, END

# from llm_client import call_llm, call_llm_json
# from routing import compute_route
# from map_generator import map_to_html
# from rag_memory import store_itinerary_memory, retrieve_similar
# from database import log_action, save_itinerary, update_itinerary


# # ---------- State ----------

# class PlannerState(TypedDict):
#     # Input
#     user_id: int
#     input_source: str          # 'form' | 'chat' | 'csv'
#     raw_input: dict            # raw form/chat/csv data
#     chat_history: list[dict]   # for chat memory
#     user_message: str          # latest user message (chat mode)

#     # Intent
#     intent: str                # 'new' | 'modify'
#     existing_itin_id: Optional[int]
#     existing_plan: Optional[dict]

#     # Structured plan data
#     plan_data: Optional[dict]

#     # RAG
#     rag_context: str

#     # Route result
#     route_result: Optional[dict]

#     # Map HTML
#     map_html: Optional[str]

#     # Explanation
#     explanation: str

#     # Output
#     final_plan: Optional[dict]
#     itinerary_id: Optional[int]

#     # Error
#     error: Optional[str]


# # ---------- Helper: parse plan_data from LLM ----------

# PLAN_SCHEMA_PROMPT = """
# Extract a structured JSON plan from the user's input.
# Return ONLY valid JSON with this exact schema:
# {
#   "user_constraints": {
#     "date": "YYYY-MM-DD or empty",
#     "budget": 5000,
#     "deadline": "HH:MM or empty",
#     "preferences": {
#       "avoid_high_traffic": false,
#       "avoid_tolls": false,
#       "optimize_for": "time"
#     }
#   },
#   "start_location": {
#     "name": "string",
#     "lat": 0.0,
#     "lng": 0.0
#   },
#   "vehicle": {
#     "start_time": "08:00",
#     "end_time": "20:00",
#     "cost_per_km": 10,
#     "capacity": 1000
#   },
#   "stops": [
#     {
#       "id": "s1",
#       "name": "string",
#       "lat": 0.0,
#       "lng": 0.0,
#       "delivery_window": "10:00-12:00",
#       "priority": 3,
#       "service_time_min": 15,
#       "package_weight": 10
#     }
#   ]
# }
# Fill in sensible defaults for missing fields.
# For location coordinates, use plausible coordinates for the mentioned city/area.
# """


# # =========================================================
# # AGENT 1: INPUT_AGENT
# # =========================================================

# def input_agent(state: PlannerState) -> PlannerState:
#     """Normalize raw_input into a structured plan_data dict."""
#     source = state.get("input_source", "form")
#     raw = state.get("raw_input", {})

#     if source == "form":
#         # Direct form input — already structured
#         state["plan_data"] = raw

#     elif source == "chat":
#         # Parse chat message into structured JSON
#         msg = state.get("user_message", "")
#         history = state.get("chat_history", [])
#         messages = history + [{"role": "user", "content": msg}]

#         # If modifying, include existing plan context
#         if state.get("existing_plan"):
#             system = PLAN_SCHEMA_PROMPT + f"\nExisting plan context: {json.dumps(state['existing_plan'])[:1000]}"
#         else:
#             system = PLAN_SCHEMA_PROMPT

#         parsed = call_llm_json(messages, system_prompt=system)
#         if "error" in parsed and "stops" not in parsed:
#             state["error"] = f"Could not parse chat input: {parsed.get('raw', '')[:200]}"
#         else:
#             state["plan_data"] = parsed

#     elif source == "csv":
#         # CSV data is pre-processed by UI into stops list
#         # raw should contain {stops: [...], start_location: ..., vehicle: ..., user_constraints: ...}
#         state["plan_data"] = raw

#     return state


# # =========================================================
# # AGENT 2: INTENT_AGENT
# # =========================================================

# INTENT_PROMPT = """
# Determine user intent from their message and context.
# Return JSON: {"intent": "new"} OR {"intent": "modify"}
# - "new" → user wants to create a completely new plan
# - "modify" → user wants to change/update/add to existing plan
# Words like: add, change, update, modify, remove, adjust → "modify"
# Words like: create, plan, new, generate, make, build → "new"
# Default to "new" if unclear.
# """


# def intent_agent(state: PlannerState) -> PlannerState:
#     """Detect if this is a new plan or modification of existing."""
#     # If no existing itinerary in session, always new
#     if not state.get("existing_itin_id"):
#         state["intent"] = "new"
#         return state

#     msg = state.get("user_message", "")
#     if not msg:
#         state["intent"] = "new"
#         return state

#     result = call_llm_json(
#         [{"role": "user", "content": msg}],
#         system_prompt=INTENT_PROMPT,
#     )
#     state["intent"] = result.get("intent", "new")
#     return state


# # =========================================================
# # AGENT 3: RAG_AGENT
# # =========================================================

# def rag_agent(state: PlannerState) -> PlannerState:
#     """Retrieve relevant past itineraries from ChromaDB."""
#     plan_data = state.get("plan_data", {})
#     query = json.dumps(plan_data)[:500]
#     user_id = state.get("user_id")

#     docs = retrieve_similar(query, user_id=user_id, n_results=2)
#     if docs:
#         context_parts = []
#         for d in docs:
#             context_parts.append(f"Similar past plan:\n{d['document'][:400]}")
#         state["rag_context"] = "\n\n".join(context_parts)
#     else:
#         state["rag_context"] = ""

#     return state


# # =========================================================
# # AGENT 4: PLANNING_AGENT
# # =========================================================

# PLANNING_PROMPT = """
# You are an expert logistics planner. Given the structured plan data,
# enhance and validate it. Ensure all stops have valid coordinates,
# delivery windows are reasonable, and priority values are 1-5.
# Return the complete plan_data JSON (same schema) with improvements applied.
# If coordinates are missing, infer from location names.
# """


# def planning_agent(state: PlannerState) -> PlannerState:
#     """Generate/enhance a new plan."""
#     plan_data = state.get("plan_data", {})
#     rag_ctx = state.get("rag_context", "")

#     system = PLANNING_PROMPT
#     if rag_ctx:
#         system += f"\n\nRelevant past plans for reference:\n{rag_ctx}"

#     enhanced = call_llm_json(
#         [{"role": "user", "content": json.dumps(plan_data)}],
#         system_prompt=system,
#     )
#     if "stops" in enhanced:
#         state["plan_data"] = enhanced
#     return state


# # =========================================================
# # AGENT 5: UPDATE_AGENT
# # =========================================================

# UPDATE_PROMPT = """
# You are modifying an existing logistics plan.
# Given the existing plan and the modification request, return the UPDATED plan JSON.
# Keep the same structure. Apply only the requested changes.
# Do NOT reset fields not mentioned in the modification request.
# Return complete updated plan_data JSON.
# """


# def update_agent(state: PlannerState) -> PlannerState:
#     """Modify existing plan based on user request."""
#     existing = state.get("existing_plan", {})
#     msg = state.get("user_message", "") or json.dumps(state.get("plan_data", {}))

#     updated = call_llm_json(
#         [{"role": "user", "content": f"Existing plan:\n{json.dumps(existing)}\n\nModification request:\n{msg}"}],
#         system_prompt=UPDATE_PROMPT,
#     )
#     if "stops" in updated or "start_location" in updated:
#         # Merge with existing
#         merged = copy.deepcopy(existing)
#         merged.update(updated)
#         state["plan_data"] = merged
#     else:
#         state["plan_data"] = existing
#     return state


# # =========================================================
# # AGENT 6: ROUTING_AGENT
# # =========================================================

# def routing_agent(state: PlannerState) -> PlannerState:
#     """Run VRP routing on the plan data."""
#     plan_data = state.get("plan_data", {})
#     if not plan_data:
#         state["error"] = "No plan data to route"
#         return state

#     result = compute_route(plan_data)
#     if "error" in result:
#         state["error"] = result["error"]
#     else:
#         state["route_result"] = result
#     return state


# # =========================================================
# # AGENT 7: MAP_AGENT
# # =========================================================

# def map_agent(state: PlannerState) -> PlannerState:
#     """Generate Folium map HTML."""
#     route_result = state.get("route_result")
#     if not route_result:
#         return state
#     try:
#         state["map_html"] = map_to_html(route_result)
#     except Exception as e:
#         state["error"] = f"Map generation failed: {e}"
#     return state


# # =========================================================
# # AGENT 8: EXPLANATION_AGENT
# # =========================================================

# EXPLANATION_PROMPT = """
# You are a friendly logistics assistant. Explain the generated route plan in 
# clear, concise language. Mention:
# - Why this route order was chosen
# - Any traffic delays or avoided
# - Budget and time efficiency
# - Any warnings or alerts
# Keep it to 3-5 bullet points. Be practical and helpful.
# """


# def explanation_agent(state: PlannerState) -> PlannerState:
#     """Generate natural language explanation of the route."""
#     route_result = state.get("route_result", {})
#     plan_data = state.get("plan_data", {})

#     context = f"Route result: {json.dumps(route_result)[:1000]}\nPlan data: {json.dumps(plan_data)[:500]}"
#     explanation = call_llm(
#         [{"role": "user", "content": context}],
#         system_prompt=EXPLANATION_PROMPT,
#         temperature=0.4,
#         max_tokens=600,
#     )
#     state["explanation"] = explanation
#     return state


# # =========================================================
# # AGENT 9: MEMORY_AGENT
# # =========================================================

# def memory_agent(state: PlannerState) -> PlannerState:
#     """Store plan in ChromaDB and SQLite."""
#     route_result = state.get("route_result", {})
#     plan_data = state.get("plan_data", {})
#     user_id = state.get("user_id", 0)
#     intent = state.get("intent", "new")

#     plan_text = json.dumps({"plan": plan_data, "route": route_result})

#     if intent == "new":
#         itin_id = save_itinerary(
#             user_id=user_id,
#             input_source=state.get("input_source", "form"),
#             input_data=json.dumps(plan_data),
#             generated_plan=plan_text,
#         )
#         state["itinerary_id"] = itin_id
#     else:
#         itin_id = state.get("existing_itin_id")
#         if itin_id:
#             update_itinerary(itin_id, plan_text, status="modified")
#             state["itinerary_id"] = itin_id

#     # Store in ChromaDB
#     store_itinerary_memory(
#         itin_id=state.get("itinerary_id", 0),
#         user_id=user_id,
#         plan_text=plan_text[:3000],
#     )

#     # Build final plan
#     state["final_plan"] = {
#         "itinerary_id": state.get("itinerary_id"),
#         "plan_data": plan_data,
#         "route_result": route_result,
#         "explanation": state.get("explanation", ""),
#         "map_html": state.get("map_html", ""),
#         "status": "modified" if intent == "modify" else "generated",
#     }
#     return state


# # =========================================================
# # AGENT 10: LOGGING_AGENT
# # =========================================================

# def logging_agent(state: PlannerState) -> PlannerState:
#     """Log the action to SQLite."""
#     user_id = state.get("user_id", 0)
#     intent = state.get("intent", "new")
#     source = state.get("input_source", "form")
#     itin_id = state.get("itinerary_id")
#     action = f"plan_{intent}_{source}"
#     detail = f"itinerary_id={itin_id}"
#     log_action(user_id, action, detail)
#     return state


# # =========================================================
# # ROUTING LOGIC (branch)
# # =========================================================

# def route_intent(state: PlannerState) -> str:
#     if state.get("intent") == "modify":
#         return "update"
#     return "plan"


# # =========================================================
# # BUILD LANGGRAPH WORKFLOW
# # =========================================================

# def build_workflow():
#     workflow = StateGraph(PlannerState)

#     # Add nodes
#     workflow.add_node("input_agent", input_agent)
#     workflow.add_node("intent_agent", intent_agent)
#     workflow.add_node("rag_agent", rag_agent)
#     workflow.add_node("planning_agent", planning_agent)
#     workflow.add_node("update_agent", update_agent)
#     workflow.add_node("routing_agent", routing_agent)
#     workflow.add_node("map_agent", map_agent)
#     workflow.add_node("explanation_agent", explanation_agent)
#     workflow.add_node("memory_agent", memory_agent)
#     workflow.add_node("logging_agent", logging_agent)

#     # Set entry
#     workflow.set_entry_point("input_agent")

#     # Edges
#     workflow.add_edge("input_agent", "intent_agent")
#     workflow.add_edge("intent_agent", "rag_agent")

#     # Conditional: new vs modify
#     workflow.add_conditional_edges(
#         "rag_agent",
#         route_intent,
#         {
#             "plan": "planning_agent",
#             "update": "update_agent",
#         }
#     )

#     workflow.add_edge("planning_agent", "routing_agent")
#     workflow.add_edge("update_agent", "routing_agent")
#     workflow.add_edge("routing_agent", "map_agent")
#     workflow.add_edge("map_agent", "explanation_agent")
#     workflow.add_edge("explanation_agent", "memory_agent")
#     workflow.add_edge("memory_agent", "logging_agent")
#     workflow.add_edge("logging_agent", END)

#     return workflow.compile()


# # Module-level compiled workflow (lazy init)
# _workflow = None


# def get_workflow():
#     global _workflow
#     if _workflow is None:
#         _workflow = build_workflow()
#     return _workflow


# def run_planner(
#     user_id: int,
#     input_source: str,
#     raw_input: dict,
#     user_message: str = "",
#     chat_history: list = None,
#     existing_itin_id: int = None,
#     existing_plan: dict = None,
# ) -> dict:
#     """
#     Main entry point. Returns final_plan dict.
#     """
#     initial_state: PlannerState = {
#         "user_id": user_id,
#         "input_source": input_source,
#         "raw_input": raw_input,
#         "chat_history": chat_history or [],
#         "user_message": user_message,
#         "intent": "new",
#         "existing_itin_id": existing_itin_id,
#         "existing_plan": existing_plan,
#         "plan_data": None,
#         "rag_context": "",
#         "route_result": None,
#         "map_html": None,
#         "explanation": "",
#         "final_plan": None,
#         "itinerary_id": None,
#         "error": None,
#     }

#     wf = get_workflow()
#     result = wf.invoke(initial_state)
#     return result

































"""
agents.py — All LangGraph agents + workflow
"""
import json
import copy
from typing import TypedDict, Optional, Annotated
import operator

from langgraph.graph import StateGraph, END

from llm_client import call_llm, call_llm_json
from routing import compute_route
from map_generator import map_to_html
from rag_memory import store_itinerary_memory, retrieve_similar
from database import log_action, save_itinerary, update_itinerary


# ---------- State ----------

class PlannerState(TypedDict):
    # Input
    user_id: int
    input_source: str          # 'form' | 'chat' | 'csv'
    raw_input: dict            # raw form/chat/csv data
    chat_history: list[dict]   # for chat memory
    user_message: str          # latest user message (chat mode)

    # Intent
    intent: str                # 'new' | 'modify'
    existing_itin_id: Optional[int]
    existing_plan: Optional[dict]

    # Structured plan data
    plan_data: Optional[dict]

    # RAG
    rag_context: str

    # Route result
    route_result: Optional[dict]

    # Map HTML
    map_html: Optional[str]

    # Explanation
    explanation: str

    # Output
    final_plan: Optional[dict]
    itinerary_id: Optional[int]

    # Error / Guardrail
    error: Optional[str]
    guardrail_triggered: bool          # True when input is off-topic
    guardrail_response: Optional[str]  # Friendly message shown to the user


# ---------- Helper: parse plan_data from LLM ----------

PLAN_SCHEMA_PROMPT = """
Extract a structured JSON plan from the user's input.
Return ONLY valid JSON with this exact schema:
{
  "user_constraints": {
    "date": "YYYY-MM-DD or empty",
    "budget": 5000,
    "deadline": "HH:MM or empty",
    "preferences": {
      "avoid_high_traffic": false,
      "avoid_tolls": false,
      "optimize_for": "time"
    }
  },
  "start_location": {
    "name": "string",
    "lat": 0.0,
    "lng": 0.0
  },
  "vehicle": {
    "start_time": "08:00",
    "end_time": "20:00",
    "cost_per_km": 10,
    "capacity": 1000
  },
  "stops": [
    {
      "id": "s1",
      "name": "string",
      "lat": 0.0,
      "lng": 0.0,
      "delivery_window": "10:00-12:00",
      "priority": 3,
      "service_time_min": 15,
      "package_weight": 10
    }
  ]
}
Fill in sensible defaults for missing fields.
For location coordinates, use plausible coordinates for the mentioned city/area.
"""


# =========================================================
# AGENT 1: INPUT_AGENT
# =========================================================

def input_agent(state: PlannerState) -> PlannerState:
    """Normalize raw_input into a structured plan_data dict."""
    # Initialise guardrail fields so they always exist in state
    state.setdefault("guardrail_triggered", False)
    state.setdefault("guardrail_response", None)

    source = state.get("input_source", "form")
    raw = state.get("raw_input", {})

    if source == "form":
        # Direct form input — already structured
        state["plan_data"] = raw

    elif source == "chat":
        # Parse chat message into structured JSON
        msg = state.get("user_message", "")
        history = state.get("chat_history", [])
        messages = history + [{"role": "user", "content": msg}]

        # If modifying, include existing plan context
        if state.get("existing_plan"):
            system = PLAN_SCHEMA_PROMPT + f"\nExisting plan context: {json.dumps(state['existing_plan'])[:1000]}"
        else:
            system = PLAN_SCHEMA_PROMPT

        parsed = call_llm_json(messages, system_prompt=system)
        if "error" in parsed and "stops" not in parsed:
            state["error"] = f"Could not parse chat input: {parsed.get('raw', '')[:200]}"
        else:
            state["plan_data"] = parsed

    elif source == "csv":
        # CSV data is pre-processed by UI into stops list
        # raw should contain {stops: [...], start_location: ..., vehicle: ..., user_constraints: ...}
        state["plan_data"] = raw

    return state


# =========================================================
# AGENT 2: GUARDRAIL_AGENT  (new)
# =========================================================

GUARDRAIL_SYSTEM_PROMPT = """
You are a strict topic classifier for a logistics route-planning assistant.

Your ONLY job is to decide whether the user's request is relevant to:
- Route planning, delivery scheduling, or itinerary optimisation
- Adding, modifying, or removing stops / waypoints
- Vehicle constraints, budgets, deadlines, or delivery windows
- Locations, addresses, maps, or geographic queries related to a plan

Return ONLY valid JSON — no prose, no markdown:
{"relevant": true}   — if the request is on-topic
{"relevant": false, "reason": "one short sentence explaining why"}  — if off-topic

Off-topic examples: jokes, general trivia, coding help, math puzzles,
weather unrelated to a route, personal advice, creative writing, harmful content.

When in doubt, return {"relevant": true} — prefer to let the planner handle edge cases.
"""


def guardrail_agent(state: PlannerState) -> PlannerState:
    """
    Classify the user request before any expensive agents run.

    Sets state["guardrail_triggered"] = True and populates
    state["guardrail_response"] with a friendly message if the
    input is off-topic, so the workflow can short-circuit cleanly.
    """
    # Already failed at parse stage — let existing error propagate
    if state.get("error"):
        return state

    # Build a concise summary of what was received
    msg = state.get("user_message", "")
    plan_data = state.get("plan_data")
    source = state.get("input_source", "form")

    if source == "chat" and msg:
        content = msg
    elif plan_data:
        stops = plan_data.get("stops", [])
        start = plan_data.get("start_location", {}).get("name", "")
        content = f"Planning a route from '{start}' with {len(stops)} stop(s)."
    elif state.get("raw_input"):
        content = json.dumps(state["raw_input"])[:400]
    else:
        # Nothing to classify — pass through
        return state

    result = call_llm_json(
        [{"role": "user", "content": content}],
        system_prompt=GUARDRAIL_SYSTEM_PROMPT,
    )

    if not result.get("relevant", True):
        reason = result.get("reason", "Your request doesn't seem related to route planning.")
        state["guardrail_triggered"] = True
        state["guardrail_response"] = (
            f"I'm a logistics route-planning assistant and can only help with "
            f"delivery routes, stops, schedules, and itinerary optimisation. "
            f"{reason} Please rephrase your request or ask something route-related!"
        )
        # Build a minimal final_plan so callers always get a consistent shape
        state["final_plan"] = {
            "itinerary_id": None,
            "plan_data": None,
            "route_result": None,
            "explanation": state["guardrail_response"],
            "map_html": "",
            "status": "rejected",
        }

    return state


def _should_continue(state: PlannerState) -> str:
    """
    Conditional edge after guardrail_agent.
    Returns 'stop' to jump straight to END, or 'continue' for the normal path.
    """
    if state.get("guardrail_triggered") or state.get("error"):
        return "stop"
    return "continue"


# =========================================================
# AGENT 3: INTENT_AGENT
# =========================================================

INTENT_PROMPT = """
Determine user intent from their message and context.
Return JSON: {"intent": "new"} OR {"intent": "modify"}
- "new" → user wants to create a completely new plan
- "modify" → user wants to change/update/add to existing plan
Words like: add, change, update, modify, remove, adjust → "modify"
Words like: create, plan, new, generate, make, build → "new"
Default to "new" if unclear.
"""


def intent_agent(state: PlannerState) -> PlannerState:
    """Detect if this is a new plan or modification of existing."""
    # If no existing itinerary in session, always new
    if not state.get("existing_itin_id"):
        state["intent"] = "new"
        return state

    msg = state.get("user_message", "")
    if not msg:
        state["intent"] = "new"
        return state

    result = call_llm_json(
        [{"role": "user", "content": msg}],
        system_prompt=INTENT_PROMPT,
    )
    state["intent"] = result.get("intent", "new")
    return state


# =========================================================
# AGENT 4: RAG_AGENT
# =========================================================

def rag_agent(state: PlannerState) -> PlannerState:
    """Retrieve relevant past itineraries from ChromaDB."""
    plan_data = state.get("plan_data", {})
    query = json.dumps(plan_data)[:500]
    user_id = state.get("user_id")

    docs = retrieve_similar(query, user_id=user_id, n_results=2)
    if docs:
        context_parts = []
        for d in docs:
            context_parts.append(f"Similar past plan:\n{d['document'][:400]}")
        state["rag_context"] = "\n\n".join(context_parts)
    else:
        state["rag_context"] = ""

    return state


# =========================================================
# AGENT 5: PLANNING_AGENT
# =========================================================

PLANNING_PROMPT = """
You are an expert logistics planner. Given the structured plan data,
enhance and validate it. Ensure all stops have valid coordinates,
delivery windows are reasonable, and priority values are 1-5.
Return the complete plan_data JSON (same schema) with improvements applied.
If coordinates are missing, infer from location names.
"""


def planning_agent(state: PlannerState) -> PlannerState:
    """Generate/enhance a new plan."""
    plan_data = state.get("plan_data", {})
    rag_ctx = state.get("rag_context", "")

    system = PLANNING_PROMPT
    if rag_ctx:
        system += f"\n\nRelevant past plans for reference:\n{rag_ctx}"

    enhanced = call_llm_json(
        [{"role": "user", "content": json.dumps(plan_data)}],
        system_prompt=system,
    )
    if "stops" in enhanced:
        state["plan_data"] = enhanced
    return state


# =========================================================
# AGENT 6: UPDATE_AGENT
# =========================================================

UPDATE_PROMPT = """
You are modifying an existing logistics plan.
Given the existing plan and the modification request, return the UPDATED plan JSON.
Keep the same structure. Apply only the requested changes.
Do NOT reset fields not mentioned in the modification request.
Return complete updated plan_data JSON.
"""


def update_agent(state: PlannerState) -> PlannerState:
    """Modify existing plan based on user request."""
    existing = state.get("existing_plan", {})
    msg = state.get("user_message", "") or json.dumps(state.get("plan_data", {}))

    updated = call_llm_json(
        [{"role": "user", "content": f"Existing plan:\n{json.dumps(existing)}\n\nModification request:\n{msg}"}],
        system_prompt=UPDATE_PROMPT,
    )
    if "stops" in updated or "start_location" in updated:
        # Merge with existing
        merged = copy.deepcopy(existing)
        merged.update(updated)
        state["plan_data"] = merged
    else:
        state["plan_data"] = existing
    return state


# =========================================================
# AGENT 7: ROUTING_AGENT
# =========================================================

def routing_agent(state: PlannerState) -> PlannerState:
    """Run VRP routing on the plan data."""
    plan_data = state.get("plan_data", {})
    if not plan_data:
        state["error"] = "No plan data to route"
        return state

    result = compute_route(plan_data)
    if "error" in result:
        state["error"] = result["error"]
    else:
        state["route_result"] = result
    return state


# =========================================================
# AGENT 8: MAP_AGENT
# =========================================================

def map_agent(state: PlannerState) -> PlannerState:
    """Generate Folium map HTML."""
    route_result = state.get("route_result")
    if not route_result:
        return state
    try:
        state["map_html"] = map_to_html(route_result)
    except Exception as e:
        state["error"] = f"Map generation failed: {e}"
    return state


# =========================================================
# AGENT 9: EXPLANATION_AGENT
# =========================================================

EXPLANATION_PROMPT = """
You are a friendly logistics assistant. Explain the generated route plan in 
clear, concise language. Mention:
- Why this route order was chosen
- Any traffic delays or avoided
- Budget and time efficiency
- Any warnings or alerts
Keep it to 3-5 bullet points. Be practical and helpful.
"""


def explanation_agent(state: PlannerState) -> PlannerState:
    """Generate natural language explanation of the route."""
    route_result = state.get("route_result", {})
    plan_data = state.get("plan_data", {})

    context = f"Route result: {json.dumps(route_result)[:1000]}\nPlan data: {json.dumps(plan_data)[:500]}"
    explanation = call_llm(
        [{"role": "user", "content": context}],
        system_prompt=EXPLANATION_PROMPT,
        temperature=0.4,
        max_tokens=600,
    )
    state["explanation"] = explanation
    return state


# =========================================================
# AGENT 10: MEMORY_AGENT
# =========================================================

def memory_agent(state: PlannerState) -> PlannerState:
    """Store plan in ChromaDB and SQLite."""
    route_result = state.get("route_result", {})
    plan_data = state.get("plan_data", {})
    user_id = state.get("user_id", 0)
    intent = state.get("intent", "new")

    plan_text = json.dumps({"plan": plan_data, "route": route_result})

    if intent == "new":
        itin_id = save_itinerary(
            user_id=user_id,
            input_source=state.get("input_source", "form"),
            input_data=json.dumps(plan_data),
            generated_plan=plan_text,
        )
        state["itinerary_id"] = itin_id
    else:
        itin_id = state.get("existing_itin_id")
        if itin_id:
            update_itinerary(itin_id, plan_text, status="modified")
            state["itinerary_id"] = itin_id

    # Store in ChromaDB
    store_itinerary_memory(
        itin_id=state.get("itinerary_id", 0),
        user_id=user_id,
        plan_text=plan_text[:3000],
    )

    # Build final plan
    state["final_plan"] = {
        "itinerary_id": state.get("itinerary_id"),
        "plan_data": plan_data,
        "route_result": route_result,
        "explanation": state.get("explanation", ""),
        "map_html": state.get("map_html", ""),
        "status": "modified" if intent == "modify" else "generated",
    }
    return state


# =========================================================
# AGENT 11: LOGGING_AGENT
# =========================================================

def logging_agent(state: PlannerState) -> PlannerState:
    """Log the action to SQLite."""
    user_id = state.get("user_id", 0)
    intent = state.get("intent", "new")
    source = state.get("input_source", "form")
    itin_id = state.get("itinerary_id")
    action = f"plan_{intent}_{source}"
    detail = f"itinerary_id={itin_id}"
    log_action(user_id, action, detail)
    return state


# =========================================================
# ROUTING LOGIC (branches)
# =========================================================

def route_intent(state: PlannerState) -> str:
    """Branch after rag_agent: new plan vs modification."""
    if state.get("intent") == "modify":
        return "update"
    return "plan"


# =========================================================
# BUILD LANGGRAPH WORKFLOW
# =========================================================

def build_workflow():
    workflow = StateGraph(PlannerState)

    # Add nodes
    workflow.add_node("input_agent", input_agent)
    workflow.add_node("guardrail_agent", guardrail_agent)   # ← new
    workflow.add_node("intent_agent", intent_agent)
    workflow.add_node("rag_agent", rag_agent)
    workflow.add_node("planning_agent", planning_agent)
    workflow.add_node("update_agent", update_agent)
    workflow.add_node("routing_agent", routing_agent)
    workflow.add_node("map_agent", map_agent)
    workflow.add_node("explanation_agent", explanation_agent)
    workflow.add_node("memory_agent", memory_agent)
    workflow.add_node("logging_agent", logging_agent)

    # Entry
    workflow.set_entry_point("input_agent")

    # input → guardrail (always)
    workflow.add_edge("input_agent", "guardrail_agent")

    # guardrail → continue normally OR short-circuit to END
    workflow.add_conditional_edges(
        "guardrail_agent",
        _should_continue,
        {
            "continue": "intent_agent",
            "stop": END,           # off-topic or parse error → skip everything
        },
    )

    workflow.add_edge("intent_agent", "rag_agent")

    # Conditional: new vs modify
    workflow.add_conditional_edges(
        "rag_agent",
        route_intent,
        {
            "plan": "planning_agent",
            "update": "update_agent",
        },
    )

    workflow.add_edge("planning_agent", "routing_agent")
    workflow.add_edge("update_agent", "routing_agent")
    workflow.add_edge("routing_agent", "map_agent")
    workflow.add_edge("map_agent", "explanation_agent")
    workflow.add_edge("explanation_agent", "memory_agent")
    workflow.add_edge("memory_agent", "logging_agent")
    workflow.add_edge("logging_agent", END)

    return workflow.compile()


# Module-level compiled workflow (lazy init)
_workflow = None


def get_workflow():
    global _workflow
    if _workflow is None:
        _workflow = build_workflow()
    return _workflow


def run_planner(
    user_id: int,
    input_source: str,
    raw_input: dict,
    user_message: str = "",
    chat_history: list = None,
    existing_itin_id: int = None,
    existing_plan: dict = None,
) -> dict:
    """
    Main entry point. Returns final_plan dict.

    When the guardrail fires, final_plan will contain:
      {
        "status": "rejected",
        "explanation": "<friendly message>",
        "itinerary_id": None,
        "plan_data": None,
        "route_result": None,
        "map_html": "",
      }
    Callers should check final_plan["status"] == "rejected" to detect this.
    """
    initial_state: PlannerState = {
        "user_id": user_id,
        "input_source": input_source,
        "raw_input": raw_input,
        "chat_history": chat_history or [],
        "user_message": user_message,
        "intent": "new",
        "existing_itin_id": existing_itin_id,
        "existing_plan": existing_plan,
        "plan_data": None,
        "rag_context": "",
        "route_result": None,
        "map_html": None,
        "explanation": "",
        "final_plan": None,
        "itinerary_id": None,
        "error": None,
        "guardrail_triggered": False,
        "guardrail_response": None,
    }

    wf = get_workflow()
    result = wf.invoke(initial_state)

    # Guarantee callers always get a final_plan dict, even on hard errors
    if result.get("final_plan") is None:
        error_msg = result.get("error", "An unexpected error occurred.")
        result["final_plan"] = {
            "itinerary_id": None,
            "plan_data": result.get("plan_data"),
            "route_result": None,
            "explanation": f"Something went wrong: {error_msg}",
            "map_html": "",
            "status": "error",
        }

    return result