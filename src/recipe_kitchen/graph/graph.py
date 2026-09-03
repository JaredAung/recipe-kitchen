"""StateGraph: caption → judge → enrich → save, or the next extract channel."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph

from recipe_kitchen.graph.nodes import (
    audio_node,
    caption_node,
    enrich_node,
    route_after_audio,
    route_after_judge,
    route_start,
    save_node,
    subtitle_node,
    sufficiency_node,
    visual_node,
)
from recipe_kitchen.schemas.extract import RecipeGraphState

type RecipeStateGraph = StateGraph[RecipeGraphState, None, RecipeGraphState, RecipeGraphState]
type CompiledRecipeGraph = CompiledStateGraph[
    RecipeGraphState, None, RecipeGraphState, RecipeGraphState
]


def build_recipe_graph() -> CompiledRecipeGraph:
    """Compile the caption → subtitle → audio → visual extraction graph."""
    graph: RecipeStateGraph = StateGraph(RecipeGraphState)
    graph.add_node("caption", caption_node)
    graph.add_node("subtitle", subtitle_node)
    graph.add_node("audio", audio_node)
    graph.add_node("visual", visual_node)
    graph.add_node("judge", sufficiency_node)
    graph.add_node("enrich", enrich_node)
    graph.add_node("save", save_node)
    graph.add_conditional_edges(
        START,
        route_start,
        {
            "caption": "caption",
            "subtitle": "subtitle",
            "audio": "audio",
            "__end__": END,
        },
    )
    graph.add_edge("caption", "judge")
    graph.add_edge("subtitle", "judge")
    graph.add_conditional_edges(
        "audio",
        route_after_audio,
        {
            "judge": "judge",
            "visual": "visual",
        },
    )
    graph.add_edge("visual", "judge")
    graph.add_conditional_edges(
        "judge",
        route_after_judge,
        {
            "enrich": "enrich",
            "subtitle": "subtitle",
            "audio": "audio",
            "visual": "visual",
            "__end__": END,
        },
    )
    graph.add_edge("enrich", "save")
    graph.add_edge("save", END)
    return graph.compile()


recipe_graph = build_recipe_graph()
