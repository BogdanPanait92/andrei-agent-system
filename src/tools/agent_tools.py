"""CrewAI tools wrapping integrations for agent use."""

import re

from crewai.tools import tool

from src.integrations.content_briefing import ContentBriefingService
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
    "status": "status",
}

_POSTING_FIELD_ALIASES = {
    "oras": "oras",
    "oraș": "oras",
    "city": "oras",
    "prioritate": "prioritate",
    "priority": "prioritate",
    "p1": "prioritate",
    "p2": "prioritate",
    "p3": "prioritate",
    "status": "status",
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


def _format_notion_records(records: list[dict[str, str]], key_fields: list[str]) -> str:
    if not records:
        return (
            "NOTION_EMPTY: 0 înregistrări în Notion (listă goală). "
            "Răspunde utilizatorului că lista e goală. NU inventa înregistrări."
        )
    lines = []
    for record in records:
        parts = [f"{field}: {record.get(field, '')}" for field in key_fields if record.get(field)]
        lines.append("- " + " | ".join(parts))
    return "\n".join(lines)


@tool("Get Family and Administrative from Notion")
def get_notion_family(status: str = "") -> str:
    """Fetch items from Notion Family & Administrative database. Optional status: To Do, In Progress, Done."""
    try:
        items = _get_notion().get_family_items(status=status or None)
        if not items:
            return "Nu există iteme în Family & Administrative."
        lines = []
        for item in items:
            title = NotionClient.extract_title(item)
            priority = NotionClient.extract_text_property(item, "Priority")
            due = NotionClient.extract_text_property(item, "Due Date")
            lines.append(f"- {title} | Prioritate: {priority} | Deadline: {due or 'N/A'}")
        return "\n".join(lines)
    except Exception as e:
        return f"Eroare la citirea Family & Administrative: {e}"


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
    """Fetch the content posting plan from Notion (Content Creation → Posting Plan)."""
    try:
        plan = _get_notion().get_posting_plan()
        if not plan:
            return "NOTION_POSTING_EMPTY: Posting Plan gol."
        lines = ["NOTION_POSTING_PLAN:"]
        for p in plan:
            rec = NotionClient.posting_plan_record(p)
            lines.append(
                f"- {rec['Titlu']} | Oras: {rec['Oras'] or '—'} | "
                f"Prioritate: {rec['Prioritate'] or '—'} | Status: {rec['Status'] or '—'}"
            )
        return "\n".join(lines)
    except Exception as e:
        return f"Eroare Posting Plan: {e}"


@tool("Get Ajut Cum Pot Items")
def get_ajut_cum_pot() -> str:
    """Fetch Ajut Cum Pot foundation items from Notion."""
    try:
        items = _get_notion().get_ajut_cum_pot_items()
        if not items:
            return "NOTION_ACP_EMPTY: Nu există iteme Ajut Cum Pot."
        lines = ["NOTION_AJUT_CUM_POT:"]
        for item in items:
            title = NotionClient.extract_title(item)
            status = NotionClient.extract_text_property(item, "Status") or "—"
            lines.append(f"- {title} | Status: {status}")
        return "\n".join(lines)
    except Exception as e:
        return f"Eroare: {e}"


@tool("Create Family and Administrative Item in Notion")
def create_notion_family_item(
    title: str, priority: str = "Medium", due_date: str = ""
) -> str:
    """Create a new item in Family & Administrative. Priority: Low, Medium, High. due_date: YYYY-MM-DD."""
    try:
        result = _get_notion().create_family_item(
            title, priority=priority, due_date=due_date or None
        )
        return f"Item creat în Family & Administrative: {title} (ID: {result.get('id', 'N/A')})"
    except Exception as e:
        return f"Eroare la creare item: {e}"


@tool("Update Family and Administrative Item in Notion")
def update_notion_family_item(
    item_title: str,
    status: str = "",
    priority: str = "",
    due_date: str = "",
) -> str:
    """Update an existing Family & Administrative item by exact title. Status: To Do, In Progress, Done."""
    try:
        notion = _get_notion()
        item = notion.find_family_item_by_title(item_title)
        if not item:
            return f"Item negăsit în Family & Administrative: {item_title}"
        notion.update_family_item(
            item["id"],
            status=status or None,
            priority=priority or None,
            due_date=due_date or None,
        )
        return f"Item actualizat: {item_title}"
    except Exception as e:
        return f"Eroare la actualizare item: {e}"


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


@tool("Save Job Entry to Notion")
def save_job(title: str, content: str, mood: str = "Reflectiv") -> str:
    """Save a work/job note to Notion Job database."""
    try:
        _get_notion().save_job_entry(title, content, mood)
        return f"Notă Job salvată: {title}"
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


@tool("List Ajut Cum Pot Partners from Notion")
def list_ajut_partners_notion() -> str:
    """List ALL Ajut Cum Pot partners from Notion. No parameters. Use only this output in your answer."""
    try:
        records = [
            {
                "Partener": NotionClient.extract_title(item),
                "Status": NotionClient.extract_text_property(item, "Status"),
            }
            for item in _get_notion().get_ajut_cum_pot_items(limit=100)
        ]
        body = _format_notion_records(records, ["Partener", "Status"])
        return f"Total parteneri în Notion: {len(records)}\n{body}"
    except Exception as e:
        return f"Eroare Notion Ajut Cum Pot: {e}. NU inventa date."


@tool("Add Ajut Cum Pot Partner to Notion")
def add_ajut_partner_notion(partener: str, detalii: str = "") -> str:
    """Add a partner in Notion Ajut Cum Pot. Required: partener (name only).
    Optional detalii: status=Active (key=value). Leave empty if user gave only the name."""
    try:
        fields = _parse_detalii(detalii, _AJUT_FIELD_ALIASES)
        _get_notion().create_ajut_cum_pot_item(
            partener,
            status=fields.get("status", ""),
        )
        extra = f" (status: {fields['status']})" if fields.get("status") else ""
        return f"Partener adăugat în Notion: {partener}{extra}"
    except Exception as e:
        return f"Eroare la adăugare partener: {e}"


@tool("Update Ajut Cum Pot Partner in Notion")
def update_ajut_partner_notion(partener: str, status: str = "") -> str:
    """Update existing Ajut Cum Pot partner by exact name."""
    try:
        notion = _get_notion()
        item = notion.find_ajut_cum_pot_by_title(partener)
        if not item:
            return f"Partener negăsit în Notion: {partener}"
        if status:
            notion.update_ajut_cum_pot_item(item["id"], status=status)
        return f"Partener actualizat: {partener}"
    except Exception as e:
        return f"Eroare la actualizare partener: {e}"


@tool("Get Content Creation Briefing")
def get_content_creation_briefing() -> str:
    """
    Read-only Content Creation briefing from Notion Posting Plan.
    Does NOT update seen Posted state. Finalize runs once at end of daily briefing.
    """
    try:
        return ContentBriefingService().build_section()
    except Exception as e:
        return f"Eroare briefing Content Creation: {e}"


@tool("List Posting Plan Items from Notion")
def list_posting_plan_notion() -> str:
    """List ALL posting plan items from Notion. No parameters. Use only this output."""
    try:
        records = [
            NotionClient.posting_plan_record(p) for p in _get_notion().get_posting_plan(limit=100)
        ]
        body = _format_notion_records(
            records,
            ["Titlu", "Oras", "Prioritate", "Status"],
        )
        return f"Total postări în Notion Posting Plan: {len(records)}\n{body}"
    except Exception as e:
        return f"Eroare Notion Posting Plan: {e}. NU inventa date."


@tool("Add Posting Plan Item to Notion")
def add_posting_plan_notion(titlu: str, detalii: str = "") -> str:
    """Add item to Notion Posting Plan. Required: titlu.
    Optional detalii: key=value pairs separated by | — oras, prioritate (p1/p2/p3), status
    Example: titlu='Momo', detalii='oras=București | prioritate=p1 | status=Planned'
    Leave detalii empty if user gave only title."""
    try:
        fields = _parse_detalii(detalii, _POSTING_FIELD_ALIASES)
        _get_notion().create_posting_plan_item(
            titlu,
            oras=fields.get("oras", ""),
            prioritate=fields.get("prioritate", ""),
            status=fields.get("status", "Planned"),
        )
        filled = [k for k, v in fields.items() if v]
        extra = f" (câmpuri: {', '.join(filled)})" if filled else " (doar titlul)"
        return f"Postare adăugată în Posting Plan: {titlu}{extra}"
    except Exception as e:
        return f"Eroare la adăugare postare: {e}"


@tool("Update Posting Plan Item in Notion")
def update_posting_plan_notion(
    titlu: str,
    oras: str = "",
    prioritate: str = "",
    status: str = "",
) -> str:
    """Update existing posting plan item by exact title."""
    try:
        notion = _get_notion()
        item = notion.find_posting_plan_by_title(titlu)
        if not item:
            return f"Postare negăsită în Posting Plan: {titlu}"
        notion.update_posting_plan_item(
            item["id"],
            oras=oras or None,
            prioritate=prioritate or None,
            status=status or None,
        )
        return f"Postare actualizată: {titlu}"
    except Exception as e:
        return f"Eroare la actualizare postare: {e}"


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
    get_notion_family,
    get_content_ideas,
    get_posting_plan,
    get_ajut_cum_pot,
    create_notion_family_item,
    update_notion_family_item,
    create_notion_idea,
    save_job,
    get_calendar_events,
    get_today_calendar,
    list_ajut_partners_notion,
    add_ajut_partner_notion,
    update_ajut_partner_notion,
    get_content_creation_briefing,
    list_posting_plan_notion,
    add_posting_plan_notion,
    update_posting_plan_notion,
    send_alert_notification,
    recall_memory,
    store_memory,
]