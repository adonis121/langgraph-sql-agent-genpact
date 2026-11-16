"""Wire the nodes into a LangGraph graph: generate_sql -> execute_sql -> answer."""
from functools import partial

from langgraph.graph import END, START, StateGraph
from sqlalchemy import Engine

from src.agent import nodes
from src.agent.state import AgentState
from src.db.database import schema_as_text


def build_graph(llm, engine: Engine, notes: str):
    """Dependencies are bound here, so tests can pass a fake LLM and a test database."""
    schema = schema_as_text(engine)  # read once, not on every question

    graph = StateGraph(AgentState)
    graph.add_node("generate_sql", partial(
        nodes.generate_sql, llm=llm, schema=schema, notes=notes, dialect=engine.dialect.name,
    ))
    graph.add_node("execute_sql", partial(nodes.execute_sql, engine=engine))
    graph.add_node("answer", partial(nodes.answer, llm=llm, notes=notes))

    graph.add_edge(START, "generate_sql")
    graph.add_edge("generate_sql", "execute_sql")
    graph.add_edge("execute_sql", "answer")
    graph.add_edge("answer", END)
    return graph.compile()
