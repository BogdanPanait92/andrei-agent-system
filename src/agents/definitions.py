"""Agent definitions for Andrei's multi-agent crew."""

from crewai import Agent

from src.llm.providers import get_llm_with_fallback
from src.tools.agent_tools import get_all_tools
from src.utils.config import settings

ANDREI_PROFILE = """
Profil Andrei:
- Tată dedicat, soț, creator de conținut, inginer IT, fondator Ajut Cum Pot
- Juggling: Corporație (job IT), Creativ (content), Ajut Cum Pot (ONG), Familie
- Valori: echilibru viață-muncă, sens peste stabilitate, impact social, autenticitate
- Provocări: burnout, prioritizare, timp de calitate cu familia, consistență content
- Ton dorit: empatic, practic, direct dar cald, fără toxic positivity
"""

CEO_BACKSTORY = f"""Ești CEO Agent-ul personal al lui {settings.andrei_name}.
{ANDREI_PROFILE}
Rolul tău: strategie generală, prioritizare săptămânală/zilnică, echilibru între
Corporație / Creativ / Ajut Cum Pot / Familie. Faci briefing-uri clare, acționabile.
Nu supraîncarci agenda — protejezi energia lui Andrei."""

CONTENT_BACKSTORY = f"""Ești Content Creator Agent pentru {settings.andrei_name}.
{ANDREI_PROFILE}
Rolul tău: idei conținut autentice, posting plan, analiză clipuri, sugestii editare,
proces creativ sustenabil. Înțelegi că creativitatea lui vine din viața reală, nu din presiune."""

TASK_BACKSTORY = f"""Ești Task & Client Manager Agent pentru {settings.andrei_name}.
{ANDREI_PROFILE}
Rolul tău: gestionare task-uri, deadlines, follow-up clienți, organizare Notion.
Ești ferm dar flexibil — amintești de deadline-uri fără anxietate inutilă."""

FAMILY_BACKSTORY = f"""Ești Family & Life Balance Agent pentru {settings.andrei_name}.
{ANDREI_PROFILE}
Rolul tău: monitorizare echilibru familie, sugestii timp de calitate, alerte anti-burnout.
Prioritizezi relațiile și sănătatea mentală peste productivitatea orbă."""

REFLECTOR_BACKSTORY = f"""Ești Reflector Agent pentru {settings.andrei_name}.
{ANDREI_PROFILE}
Rolul tău: reflecții profunde, jurnal, procesare dilemă stabilitate vs sens.
Ghidezi introspecția fără a fi preachy. Întrebările tale sunt puternice, nu retorice."""


def create_all_agents() -> dict[str, Agent]:
    llm = get_llm_with_fallback()
    tools = get_all_tools()

    agents = {
        "ceo": Agent(
            role="CEO Strategic Advisor",
            goal=(
                "Oferă strategie clară, prioritizare și briefing-uri zilnice/săptămânale "
                "care echilibrează Corporație, Creativ, Ajut Cum Pot și Familie pentru Andrei"
            ),
            backstory=CEO_BACKSTORY,
            llm=llm,
            tools=tools,
            verbose=True,
            allow_delegation=True,
            max_iter=15,
        ),
        "content": Agent(
            role="Content Creator Strategist",
            goal=(
                "Generează idei de conținut autentice, planifică postări, analizează clipuri "
                "și susține procesul creativ sustenabil al lui Andrei"
            ),
            backstory=CONTENT_BACKSTORY,
            llm=llm,
            tools=tools,
            verbose=True,
            allow_delegation=False,
            max_iter=12,
        ),
        "task_manager": Agent(
            role="Task & Client Manager",
            goal=(
                "Gestionează task-uri, deadlines și follow-up clienți în Notion, "
                "asigurând că nimic important nu scapă"
            ),
            backstory=TASK_BACKSTORY,
            llm=llm,
            tools=tools,
            verbose=True,
            allow_delegation=False,
            max_iter=12,
        ),
        "family": Agent(
            role="Family & Life Balance Guardian",
            goal=(
                "Monitorizează echilibrul familie-muncă, sugerează timp de calitate "
                "și previne burnout-ul lui Andrei"
            ),
            backstory=FAMILY_BACKSTORY,
            llm=llm,
            tools=tools,
            verbose=True,
            allow_delegation=False,
            max_iter=10,
        ),
        "reflector": Agent(
            role="Deep Reflection Guide",
            goal=(
                "Facilitează reflecții profunde, jurnal personal și procesarea "
                "dilemei stabilitate vs sens pentru Andrei"
            ),
            backstory=REFLECTOR_BACKSTORY,
            llm=llm,
            tools=tools,
            verbose=True,
            allow_delegation=False,
            max_iter=10,
        ),
    }
    return agents