"""Wire the nodes into a LangGraph graph.

generate_sql -> validate_sql -> execute_sql -> check_result -> answer
Any failure loops back to generate_sql with the error, until MAX_ATTEMPTS, then give_up.
"""
from functools import partial

from langgraph.graph import END, START, StateGraph
from sqlalchemy import Engine

from src.agent import nodes
from src.agent.nodes import MAX_ATTEMPTS
from src.agent.state import AgentState
from src.db.database import schema_as_text


# --- Routing: each returns the name of the next node ---------------------------

def retry_or_give_up(state: AgentState) -> str:
    return "generate_sql" if state["attempts"] < MAX_ATTEMPTS else "give_up"


def after_validate(state: AgentState) -> str:
    return retry_or_give_up(state) if state["error"] else "execute_sql"


def after_execute(state: AgentState) -> str:
    return retry_or_give_up(state) if state["error"] else "check_result"


def after_check(state: AgentState) -> str:
    return retry_or_give_up(state) if state["error"] else "answer"


# --- Graph ---------------------------------------------------------------------

def build_graph(llm, engine: Engine, notes: str):
    """Dependencies are bound here, so tests can pass a fake LLM and a test database."""
    schema = schema_as_text(engine)  # read once, not on every question

    graph = StateGraph(AgentState)
    graph.add_node("generate_sql", partial(
        nodes.generate_sql, llm=llm, schema=schema, notes=notes, dialect=engine.dialect.name,
    ))
    graph.add_node("validate_sql", nodes.validate_sql)
    graph.add_node("execute_sql", partial(nodes.execute_sql, engine=engine))
    graph.add_node("check_result", nodes.check_result)
    graph.add_node("answer", partial(nodes.answer, llm=llm, notes=notes))
    graph.add_node("give_up", nodes.give_up)

    graph.add_edge(START, "generate_sql")
    graph.add_edge("generate_sql", "validate_sql")
    graph.add_conditional_edges(
        "validate_sql", after_validate, ["execute_sql", "generate_sql", "give_up"])
    graph.add_conditional_edges(
        "execute_sql", after_execute, ["check_result", "generate_sql", "give_up"])
    graph.add_conditional_edges(
        "check_result", after_check, ["answer", "generate_sql", "give_up"])
    graph.add_edge("answer", END)
    graph.add_edge("give_up", END)
    return graph.compile()
