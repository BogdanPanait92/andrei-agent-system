"""LangGraph workflow for orchestrated agent execution."""

from typing import Annotated, TypedDict

from langgraph.graph import END, StateGraph
from langgraph.graph.message import add_messages

from src.crew.main_crew import AndreiCrew
from src.integrations.memory import MemoryStore
from src.integrations.notion import NotionClient
from src.integrations.notifier import get_notifier
from src.utils.logging import get_logger

logger = get_logger(__name__)


class AgentState(TypedDict):
    messages: Annotated[list, add_messages]
    mode: str
    query: str
    ceo_output: str
    content_output: str
    task_output: str
    family_output: str
    reflector_output: str
    final_output: str
    notifications_sent: bool


def _gather_context(state: AgentState) -> AgentState:
    memory = MemoryStore()
    memory.initialize()
    ctx = memory.get_context_for_agents(state.get("query", ""))
    state["messages"] = state.get("messages", []) + [{"role": "system", "content": ctx}]
    return state


def _run_crew_node(state: AgentState) -> AgentState:
    crew = AndreiCrew()
    result = crew.run(mode=state.get("mode", "custom"), query=state.get("query", ""))
    state["final_output"] = result
    return state


def _notify_node(state: AgentState) -> AgentState:
    notifier = get_notifier()
    if not notifier.enabled:
        state["notifications_sent"] = False
        return state

    mode = state.get("mode", "custom")
    output = state.get("final_output", "")

    if mode == "daily":
        notifier.send_daily_briefing(output[:3500])
    elif mode == "weekly":
        notifier.send_weekly_review(output[:3500])
    else:
        notifier.send_message(f"🤖 Răspuns Crew\n\n{output[:3500]}")

    state["notifications_sent"] = True
    return state


def _save_notion_node(state: AgentState) -> AgentState:
    try:
        notion = NotionClient()
        mode = state.get("mode", "custom")
        output = state.get("final_output", "")
        title = {"daily": "Daily Briefing", "weekly": "Weekly Review"}.get(mode, "Crew Output")
        notion.save_briefing(title, output, briefing_type=mode)
    except Exception as e:
        logger.warning("notion_save_skipped", error=str(e))
    return state


class AndreiWorkflow:
    def __init__(self) -> None:
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        workflow = StateGraph(AgentState)

        workflow.add_node("gather_context", _gather_context)
        workflow.add_node("run_crew", _run_crew_node)
        workflow.add_node("notify", _notify_node)
        workflow.add_node("save_notion", _save_notion_node)

        workflow.set_entry_point("gather_context")
        workflow.add_edge("gather_context", "run_crew")
        workflow.add_edge("run_crew", "notify")
        workflow.add_edge("notify", "save_notion")
        workflow.add_edge("save_notion", END)

        return workflow.compile()

    def run(self, mode: str = "custom", query: str = "") -> str:
        initial: AgentState = {
            "messages": [],
            "mode": mode,
            "query": query,
            "ceo_output": "",
            "content_output": "",
            "task_output": "",
            "family_output": "",
            "reflector_output": "",
            "final_output": "",
            "notifications_sent": False,
        }
        result = self.graph.invoke(initial)
        return result.get("final_output", "")


def run_workflow(mode: str = "custom", query: str = "") -> str:
    return AndreiWorkflow().run(mode=mode, query=query)