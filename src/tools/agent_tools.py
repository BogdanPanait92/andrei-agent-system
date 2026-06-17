"""CrewAI tools wrapping integrations for agent use."""

from crewai.tools import tool

from src.integrations.google_services import GoogleServices
from src.integrations.memory import MemoryStore
from src.integrations.notion import NotionClient
from src.integrations.notifier import get_notifier

_notion: NotionClient | None = None
_google: GoogleServices | None = None
_notifier = None
_memory: MemoryStore | None = None


def _get_notion() -> NotionClient:
    global _notion
    if _notion is None:
        _notion = NotionClient()
    return _notion


def _get_google() -> GoogleServices:
    global _google
    if _google is None:
        _google = GoogleServices()
    return _google


def _get_notifier():
    global _notifier
    if _notifier is None:
        _notifier = get_notifier()
    return _notifier


def _get_memory() -> MemoryStore:
    global _memory
    if _memory is None:
        _memory = MemoryStore()
    return _memory


@tool("Get Tasks from Notion")
def get_notion_tasks(status: str = "") -> str:
    """Fetch tasks from Notion task dashboard. Optional status filter: To Do, In Progress, Done."""
    try:
        tasks = _get_notion().get_tasks(status=status or None)
        if not tasks:
            return "Nu există task-uri în Notion."
        lines = []
        for t in tasks:
            title = NotionClient.extract_title(t)
            priority = NotionClient.extract_text_property(t, "Priority")
            due = NotionClient.extract_text_property(t, "Due Date")
            lines.append(f"- {title} | Prioritate: {priority} | Deadline: {due or 'N/A'}")
        return "\n".join(lines)
    except Exception as e:
        return f"Eroare la citirea task-urilor: {e}"


@tool("Get Content Ideas from Notion")
def get_content_ideas() -> str:
    """Fetch content ideas from Notion ideas database."""
    try:
        ideas = _get_notion().get_ideas()
        if not ideas:
            return "Nu există idei de conținut."
        return "\n".join(f"- {NotionClient.extract_title(i)}" for i in ideas)
    except Exception as e:
        return f"Eroare: {e}"


@tool("Get Posting Plan from Notion")
def get_posting_plan() -> str:
    """Fetch the content posting plan from Notion."""
    try:
        plan = _get_notion().get_posting_plan()
        if not plan:
            return "Posting plan gol."
        lines = []
        for p in plan:
            title = NotionClient.extract_title(p)
            date = NotionClient.extract_text_property(p, "Date")
            lines.append(f"- {date or 'TBD'}: {title}")
        return "\n".join(lines)
    except Exception as e:
        return f"Eroare: {e}"


@tool("Get Ajut Cum Pot Items")
def get_ajut_cum_pot() -> str:
    """Fetch Ajut Cum Pot foundation items from Notion."""
    try:
        items = _get_notion().get_ajut_cum_pot_items()
        if not items:
            return "Nu există iteme Ajut Cum Pot."
        return "\n".join(f"- {NotionClient.extract_title(i)}" for i in items)
    except Exception as e:
        return f"Eroare: {e}"


@tool("Create Task in Notion")
def create_notion_task(title: str, priority: str = "Medium", due_date: str = "") -> str:
    """Create a new task in Notion. Priority: Low, Medium, High. due_date format: YYYY-MM-DD."""
    try:
        result = _get_notion().create_task(title, priority=priority, due_date=due_date or None)
        return f"Task creat: {title} (ID: {result.get('id', 'N/A')})"
    except Exception as e:
        return f"Eroare la creare task: {e}"


@tool("Save Journal Entry to Notion")
def save_journal(title: str, content: str, mood: str = "Reflectiv") -> str:
    """Save a journal/reflection entry to Notion journal database."""
    try:
        _get_notion().save_journal_entry(title, content, mood)
        return f"Jurnal salvat: {title}"
    except Exception as e:
        return f"Eroare: {e}"


@tool("Get Google Calendar Events")
def get_calendar_events(days: int = 7) -> str:
    """Get upcoming Google Calendar events for the next N days."""
    try:
        events = _get_google().get_upcoming_events(days=days)
        return GoogleServices.format_events_for_context(events)
    except Exception as e:
        return f"Eroare calendar: {e}"


@tool("Get Today's Calendar")
def get_today_calendar() -> str:
    """Get today's Google Calendar events."""
    try:
        events = _get_google().get_today_events()
        return GoogleServices.format_events_for_context(events)
    except Exception as e:
        return f"Eroare: {e}"


@tool("Send Alert Notification")
def send_alert_notification(alert_type: str, message: str) -> str:
    """Send an alert via configured notifier (Telegram or WhatsApp). Types: deadline, family, burnout, content, balance."""
    try:
        ok = _get_notifier().send_alert(alert_type, message)
        return "Alertă trimisă." if ok else "Notifier neconfigurat sau eșuat."
    except Exception as e:
        return f"Eroare notifier: {e}"


@tool("Recall Agent Memory")
def recall_memory(query: str) -> str:
    """Recall relevant context from persistent agent memory."""
    try:
        ctx = _get_memory().get_context_for_agents(query)
        return ctx or "Nicio memorie relevantă găsită."
    except Exception as e:
        return f"Eroare memorie: {e}"


@tool("Store Agent Memory")
def store_memory(content: str, agent: str = "system", category: str = "general") -> str:
    """Store important insight in persistent memory for future reference."""
    try:
        ok = _get_memory().store(content, agent=agent, category=category)
        return "Memorie salvată." if ok else "Memorie neconfigurată."
    except Exception as e:
        return f"Eroare: {e}"


def get_all_tools() -> list:
    return [
        get_notion_tasks,
        get_content_ideas,
        get_posting_plan,
        get_ajut_cum_pot,
        create_notion_task,
        save_journal,
        get_calendar_events,
        get_today_calendar,
        send_alert_notification,
        recall_memory,
        store_memory,
    ]