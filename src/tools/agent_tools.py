"""CrewAI tools wrapping integrations for agent use."""

import re

from crewai.tools import tool

from src.integrations.content_briefing import ContentBriefingService
from src.integrations.google_services import GoogleServices
from src.integrations.google_sheets import GoogleSheetsService
from src.integrations.memory import MemoryStore
from src.integrations.notion import NotionClient
from src.integrations.notifier import get_notifier

_notion: NotionClient | None = None
_google: GoogleServices | None = None
_sheets: GoogleSheetsService | None = None
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


def _get_sheets() -> GoogleSheetsService:
    global _sheets
    if _sheets is None:
        _sheets = GoogleSheetsService()
    return _sheets


def _parse_detalii(detalii: str, aliases: dict[str, str]) -> dict[str, str]:
    """Parse 'locatie=Cluj | contact=Ana' into canonical field names."""
    result: dict[str, str] = {}
    if not detalii or not detalii.strip():
        return result
    for chunk in re.split(r"[|\n;]+", detalii):
        chunk = chunk.strip()
        if not chunk or "=" not in chunk:
            continue
        key, _, value = chunk.partition("=")
        key = key.strip().lower().replace(" ", "_")
        value = value.strip()
        if not value:
            continue
        canonical = aliases.get(key)
        if canonical:
            result[canonical] = value
    return result


_AJUT_FIELD_ALIASES = {
    "contact": "persoana_contact",
    "persoana": "persoana_contact",
    "persoana_contact": "persoana_contact",
    "telefon": "telefon_email",
    "email": "telefon_email",
    "telefon_email": "telefon_email",
    "locatie": "locatie",
    "locație": "locatie",
    "adresa": "locatie",
    "status": "status",
    "note": "note",
    "nota": "note",
    "urmatorul_pas": "urmatorul_pas",
    "următorul_pas": "urmatorul_pas",
}

_EDITOR_FIELD_ALIASES = {
    "link": "link_video",
    "link_video": "link_video",
    "video": "link_video",
    "instructiuni": "instructiuni",
    "instrucțiuni": "instructiuni",
    "status": "status",
    "assignat": "assignat",
    "editor": "assignat",
    "deadline": "deadline",
    "note": "note",
    "nota": "note",
}


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
def get_content_ideas(status: str = "") -> str:
    """
    Fetch ideas from Notion Ideas database.
    Optional status filter: Draft, In evaluare, In lucru, Arhivat (empty = all).
    Pass only status string, e.g. status='Draft'. Do NOT invent idea data.
    """
    try:
        notion = _get_notion()
        resolved = NotionClient.normalize_idea_status(status) if status else None
        if status and not resolved:
            return (
                f"NOTION_IDEAS_ERROR: Status invalid '{status}'. "
                f"Valori: Draft, In evaluare, In lucru, Arhivat."
            )
        ideas = notion.get_ideas(status=status or None)
        if not ideas:
            label = f" cu status '{resolved}'" if resolved else ""
            return f"NOTION_IDEAS_EMPTY: Nu există idei{label} în Notion Ideas."
        header = (
            f"NOTION_IDEAS ({len(ideas)} idei, status={resolved}):"
            if resolved
            else f"NOTION_IDEAS ({len(ideas)} idei din baza Ideas):"
        )
        lines = [header]
        for idea in ideas:
            title = NotionClient.extract_title(idea)
            category = NotionClient.extract_text_property(idea, "Category") or "—"
            idea_status = NotionClient.extract_text_property(idea, "status") or "—"
            notes = NotionClient.extract_text_property(idea, "Notes") or "—"
            lines.append(
                f"- {title} | Status: {idea_status} | Categorie: {category} | Notes: {notes}"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"NOTION_IDEAS_ERROR: {e}"


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


@tool("Update Task in Notion")
def update_notion_task(
    task_title: str,
    status: str = "",
    priority: str = "",
    due_date: str = "",
) -> str:
    """Update an existing Notion task by exact title. Status: To Do, In Progress, Done."""
    try:
        notion = _get_notion()
        task = notion.find_task_by_title(task_title)
        if not task:
            return f"Task negăsit: {task_title}"
        notion.update_task(
            task["id"],
            status=status or None,
            priority=priority or None,
            due_date=due_date or None,
        )
        return f"Task actualizat: {task_title}"
    except Exception as e:
        return f"Eroare la actualizare task: {e}"


@tool("Create Content Idea in Notion")
def create_notion_idea(
    title: str,
    category: str = "General",
    notes: str = "",
    status: str = "Draft",
) -> str:
    """Save a new idea in Notion. New ideas default to status Draft."""
    try:
        result = _get_notion().create_idea(
            title, category=category, notes=notes, status=status or "Draft"
        )
        saved_status = NotionClient.extract_text_property(result, "status") or "Draft"
        return f"Idee creată: {title} | Status: {saved_status} (ID: {result.get('id', 'N/A')})"
    except Exception as e:
        return f"Eroare la creare idee: {e}"


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


@tool("List Ajut Cum Pot Partners")
def list_ajut_partners_sheet() -> str:
    """List ALL Ajut Cum Pot partners from Google Sheets. No parameters. Use only this output in your answer."""
    try:
        records = _get_sheets().get_ajut_partners()
        count = len(records)
        body = GoogleSheetsService.format_records(
            records,
            ["Partener", "Persoana contact", "Locatie", "Status", "Urmatorul pas"],
        )
        return f"Total parteneri in Sheets: {count}\n{body}"
    except Exception as e:
        return f"Eroare Sheets Ajut Cum Pot: {e}. NU inventa date."


@tool("Add Ajut Cum Pot Partner to Sheets")
def add_ajut_partner_sheet(partener: str, detalii: str = "") -> str:
    """Add a partner row. Required: partener (name only).
    Optional detalii: ONLY fields the user explicitly said, as key=value pairs separated by |
    Allowed keys: contact, telefon, locatie, status, note, urmatorul_pas
    Example: partener='ONG X', detalii='locatie=Bucuresti | contact=Ana'
    If user gives only the name, leave detalii empty. Do NOT invent missing fields."""
    try:
        fields = _parse_detalii(detalii, _AJUT_FIELD_ALIASES)
        _get_sheets().add_ajut_partner(partener=partener, **fields)
        filled = [k for k, v in fields.items() if v]
        extra = f" (campuri: {', '.join(filled)})" if filled else " (doar numele, restul gol)"
        return f"Partener adaugat in Sheets: {partener}{extra}"
    except Exception as e:
        return f"Eroare la adaugare partener: {e}"


@tool("Update Ajut Cum Pot Partner in Sheets")
def update_ajut_partner_sheet(
    partener: str,
    persoana_contact: str = "",
    telefon_email: str = "",
    locatie: str = "",
    status: str = "",
    note: str = "",
    urmatorul_pas: str = "",
) -> str:
    """Update existing Ajut Cum Pot partner row by exact partner name."""
    try:
        ok = _get_sheets().update_ajut_partner(
            partener,
            persoana_contact=persoana_contact,
            telefon_email=telefon_email,
            locatie=locatie,
            status=status,
            note=note,
            urmatorul_pas=urmatorul_pas,
        )
        return f"Partener actualizat: {partener}" if ok else f"Partener negasit: {partener}"
    except Exception as e:
        return f"Eroare la actualizare partener: {e}"


@tool("Get Content Creation Briefing")
def get_content_creation_briefing() -> str:
    """Content Creation sheet briefing: rows missing link/instructions + newly Done items to post. No parameters."""
    try:
        return ContentBriefingService().run()
    except Exception as e:
        return f"Eroare briefing Content Creation: {e}"


@tool("List Editor Pipeline Materials")
def list_editor_pipeline_sheet() -> str:
    """List ALL video materials for editors from Google Sheets. No parameters. Use only this output."""
    try:
        records = _get_sheets().get_editor_materials()
        count = len(records)
        body = GoogleSheetsService.format_records(
            records,
            ["Titlu", "Link video", "Status", "Assignat", "Deadline"],
        )
        return f"Total materiale in Sheets: {count}\n{body}"
    except Exception as e:
        return f"Eroare Sheets editori: {e}. NU inventa date."


@tool("Add Editor Material to Sheets")
def add_editor_material_sheet(titlu: str, detalii: str = "") -> str:
    """Add editor material row. Required: titlu.
    Optional detalii: ONLY fields the user said, key=value pairs separated by |
    Allowed keys: link, instructiuni, status, assignat, deadline, note
    Example: titlu='Clip vlog', detalii='link=https://... | assignat=Maria'
    Leave detalii empty if user gave only title. Do NOT invent missing fields."""
    try:
        fields = _parse_detalii(detalii, _EDITOR_FIELD_ALIASES)
        _get_sheets().add_editor_material(titlu=titlu, **fields)
        filled = [k for k, v in fields.items() if v]
        extra = f" (campuri: {', '.join(filled)})" if filled else " (doar titlul, restul gol)"
        return f"Material adaugat pentru editori: {titlu}{extra}"
    except Exception as e:
        return f"Eroare la adaugare material: {e}"


@tool("Update Editor Material in Sheets")
def update_editor_material_sheet(
    titlu: str,
    link_video: str = "",
    instructiuni: str = "",
    status: str = "",
    assignat: str = "",
    deadline: str = "",
    note: str = "",
) -> str:
    """Update existing editor material row by exact title."""
    try:
        ok = _get_sheets().update_editor_material(
            titlu,
            link_video=link_video,
            instructiuni=instructiuni,
            status=status,
            assignat=assignat,
            deadline=deadline,
            note=note,
        )
        return f"Material actualizat: {titlu}" if ok else f"Material negasit: {titlu}"
    except Exception as e:
        return f"Eroare la actualizare material: {e}"


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
    return _ALL_TOOLS


def get_idea_mode_tools() -> list:
    """Tools for idea mode — Notion save is handled programmatically after the plan."""
    return [t for t in _ALL_TOOLS if t.name != "Create Content Idea in Notion"]


_ALL_TOOLS = [
        get_notion_tasks,
        get_content_ideas,
        get_posting_plan,
        get_ajut_cum_pot,
        create_notion_task,
        update_notion_task,
        create_notion_idea,
        save_journal,
        get_calendar_events,
        get_today_calendar,
        list_ajut_partners_sheet,
        add_ajut_partner_sheet,
        update_ajut_partner_sheet,
        get_content_creation_briefing,
        list_editor_pipeline_sheet,
        add_editor_material_sheet,
        update_editor_material_sheet,
        send_alert_notification,
        recall_memory,
        store_memory,
]