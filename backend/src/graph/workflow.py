"""
This module defines the DAG (Directed Acyclic Graph) that orchestrates the video compliance
audit process.
It connects the nodes using StateGraph from langgraph

START -> index_video_node -> audit_content_node -> END
"""

from langgraph.graph import StateGraph, END
from backend.src.graph.states import VideoAuditState

from backend.src.graph.nodes import video_indexer, audit_content


def create_graph():
    """
    Constructs and Compiles the Graph
    """
    workflow = StateGraph(VideoAuditState)

    workflow.add_node("indexer", video_indexer)
    workflow.add_node("auditor", audit_content)

    workflow.set_entry_point("indexer")
    workflow.add_edge("indexer", "auditor")
    workflow.add_edge("auditor", END)

    app = workflow.compile()

    return app


app = create_graph()
