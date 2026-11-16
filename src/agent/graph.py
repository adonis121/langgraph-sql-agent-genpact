"""Wire the nodes into a LangGraph graph.

plan -> generate_sql -> validate_sql -> execute_sql -> check_result -> (next step | answer)
- plan can also end early (decline) or pause to ask the user (ask_user, then plan again).
- Any SQL failure loops back to generate_sql with the error, until MAX_ATTEMPTS, then give_up.
"""
from functools import partial

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from sqlalchemy import Engine

from src.agent import nodes
from src.agent.nodes import MAX_ATTEMPTS
from src.agent.state import AgentState
from src.db.database import schema_as_text


# --- Routing: each returns the name of the next node ---------------------------

def after_plan(state: AgentState) -> str:
    decision = state["plan"]["decision"]
    if decision == "answerable":
        return "generate_sql"
    # "is None", not falsy: an empty reply still counts as asked, so we never ask twice.
    if decision == "needs_clarification" and state["clarification"] is None:
        return "ask_user"
    return "decline"  # out of scope, or still unclear after one clarification


def retry_or_give_up(state: AgentState) -> str:
    return "generate_sql" if state["attempts"] < MAX_ATTEMPTS else "give_up"


def after_validate(state: AgentState) -> str:
    return retry_or_give_up(state) if state["error"] else "execute_sql"


def after_execute(state: AgentState) -> str:
    return retry_or_give_up(state) if state["error"] else "check_result"


def after_check(state: AgentState) -> str:
    if state["error"]:
        return retry_or_give_up(state)
    # check_result already moved step_index on to the next step.
    return "generate_sql" if state["step_index"] < len(state["steps"]) else "answer"


# --- Graph ---------------------------------------------------------------------

def build_graph(llm, engine: Engine, notes: str, checkpointer=None):
    """Dependencies are bound here, so tests can pass a fake LLM and a test database.

    The checkpointer saves the state between steps; interrupt() in ask_user needs it to
    pause the run and resume it later with the user's reply.
    """
    schema = schema_as_text(engine)  # read once, not on every question

    graph = StateGraph(AgentState)
    graph.add_node("plan", partial(nodes.plan, llm=llm, schema=schema, notes=notes))
    graph.add_node("ask_user", nodes.ask_user)
    graph.add_node("decline", nodes.decline)
    graph.add_node("generate_sql", partial(
        nodes.generate_sql, llm=llm, schema=schema, notes=notes, dialect=engine.dialect.name,
    ))
    graph.add_node("validate_sql", nodes.validate_sql)
    graph.add_node("execute_sql", partial(nodes.execute_sql, engine=engine))
    graph.add_node("check_result", nodes.check_result)
    graph.add_node("answer", partial(nodes.answer, llm=llm, notes=notes))
    graph.add_node("give_up", nodes.give_up)

    graph.add_edge(START, "plan")
    graph.add_conditional_edges("plan", after_plan, ["generate_sql", "ask_user", "decline"])
    graph.add_edge("ask_user", "plan")
    graph.add_edge("generate_sql", "validate_sql")
    graph.add_conditional_edges(
        "validate_sql", after_validate, ["execute_sql", "generate_sql", "give_up"])
    graph.add_conditional_edges(
        "execute_sql", after_execute, ["check_result", "generate_sql", "give_up"])
    graph.add_conditional_edges(
        "check_result", after_check, ["answer", "generate_sql", "give_up"])
    graph.add_edge("answer", END)
    graph.add_edge("give_up", END)
    graph.add_edge("decline", END)
    return graph.compile(checkpointer=checkpointer or InMemorySaver())
