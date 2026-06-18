"""Main CrewAI crew orchestrating all 5 agents."""

from crewai import Crew, Process, Task

from src.agents.definitions import create_all_agents, create_idea_mode_agent
from src.integrations.content_briefing import append_to_daily_briefing
from src.integrations.memory import MemoryStore
from src.integrations.notion import NotionClient
from src.utils.config import settings
from src.utils.logging import get_logger

logger = get_logger(__name__)


class AndreiCrew:
    def __init__(self) -> None:
        self.agents = create_all_agents()
        self.memory = MemoryStore()

    def _build_context(self, user_query: str) -> str:
        self.memory.initialize()
        mem_ctx = self.memory.get_context_for_agents(user_query)
        return f"""
Query utilizator: {user_query}
Profil: Andrei - tată, soț, creator conținut, inginer IT, fondator Ajut Cum Pot
Data: {settings.timezone}
{mem_ctx}
"""

    def create_daily_briefing_tasks(self) -> list[Task]:
        ctx = self._build_context("daily briefing complet")
        return [
            Task(
                description=f"""{ctx}
Creează briefing zilnic pentru Andrei:
1. Verifică task-urile din Notion (priorități azi)
2. Verifică calendarul Google (azi + 2 zile)
3. Evaluează echilibrul muncă-familie
4. 3 priorități clare pentru azi
5. O sugestie de timp de calitate cu familia
Secțiunea Content Creation (Sheets) este adăugată automat la final — nu o inventa.
Răspunde în română, concis, empatic.""",
                expected_output="Briefing zilnic structurat cu priorități, calendar, alerte și sugestie familie.",
                agent=self.agents["ceo"],
            ),
            Task(
                description="""Pe baza briefing-ului CEO, verifică content pipeline-ul:
- Idei noi sau postări planificate din Notion
- Secțiunea Content Creation din Sheets (lipsuri + Done) vine automat la finalul briefing-ului""",
                expected_output="Update scurt content pipeline + sugestie opțională.",
                agent=self.agents["content"],
                context=[],
            ),
            Task(
                description="""Verifică deadlines apropiate și follow-up-uri clienți necesare azi.""",
                expected_output="Listă deadlines + acțiuni follow-up.",
                agent=self.agents["task_manager"],
            ),
        ]

    def create_weekly_review_tasks(self) -> list[Task]:
        ctx = self._build_context("weekly review duminică")
        return [
            Task(
                description=f"""{ctx}
Creează Weekly Review detaliat pentru Andrei:
1. Recap săptămână: Corporație, Creativ, Ajut Cum Pot, Familie
2. Ce a mers bine / ce nu
3. Metrici subiective de echilibru (1-10)
4. Priorități săptămâna viitoare
5. Recomandări strategice""",
                expected_output="Weekly review complet, structurat, în română.",
                agent=self.agents["ceo"],
            ),
            Task(
                description="Analizează performanța content pipeline săptămâna trecută și planul pentru următoarea.",
                expected_output="Analiză content + plan săptămâna viitoare.",
                agent=self.agents["content"],
            ),
            Task(
                description="Evaluează echilibrul familie și semne de burnout. Sugerează ajustări.",
                expected_output="Evaluare wellbeing + recomandări concrete.",
                agent=self.agents["family"],
            ),
            Task(
                description="""Reflecție profundă: dilemă stabilitate vs sens.
Pune 2-3 întrebări puternice pentru jurnalul săptămânii.""",
                expected_output="Reflecție + întrebări jurnal.",
                agent=self.agents["reflector"],
            ),
        ]

    def create_idea_tasks(self, user_query: str) -> list[Task]:
        """Focused mode: implementation plan for a new idea."""
        ctx = self._build_context(user_query)
        return [
            Task(
                description=f"""{ctx}
Andrei îți împărtășește o idee nouă. Oferă sugestii practice de implementare.

Ideea: {user_query}

Structură răspuns (în română):
1. **Rezumat** — reformulează ideea în 1-2 propoziții
2. **De ce merită** — valoare pentru Corporație / Creativ / Ajut Cum Pot / Familie
3. **Pași de implementare** — 3-7 pași concreți, ordonați
4. **Quick win** — ce poate face Andrei azi sau în 30 min
5. **Resurse** — timp estimat, cost aproximativ, ajutor necesar
6. **Atenție** — riscuri, dependențe, ce să amâne
7. **Următorul pas** — o singură acțiune clară pentru azi

Planul va fi salvat automat în Notion Ideas după generare — nu e nevoie de tool separat.
Fii practic, nu teoretic. Protejează echilibrul vieții lui Andrei.""",
                expected_output="Plan de implementare structurat, acționabil, în română.",
                agent=self.agents["content"],
            ),
        ]

    def create_chat_tasks(
        self,
        user_query: str,
        conversation_context: str = "",
        web_search_context: str = "",
    ) -> list[Task]:
        """Single-agent conversational mode for Discord/Telegram chat."""
        ctx = self._build_context(user_query)
        conv_block = f"\n{conversation_context}\n" if conversation_context else ""
        web_block = f"\n{web_search_context}\n" if web_search_context else ""
        return [
            Task(
                description=f"""{ctx}
Ești în mod conversațional — {settings.user_name} te contactează direct.
{conv_block}{web_block}
Cerere curentă: {user_query}

Instrucțiuni:
- Răspunde direct la întrebare, concis dar complet
- Pentru date (Sheets, Notion, Calendar) APELEAZĂ tool-ul și folosește DOAR output-ul lui
- Tool-urile fără parametri se apelează cu input gol — NU trimite JSON inventat ca input
- INTERZIS să inventezi parteneri, task-uri, idei, evenimente sau materiale
- Dacă tool-ul returnează SHEETS_EMPTY, NOTION_IDEAS_EMPTY sau 0, spune că lista e goală
- Pentru idei în draft: apelează Get Content Ideas cu status='Draft'
- Dacă tool-ul returnează EROARE sau eșuează apelul, raportează eroarea — NU completa cu date fictive
- Poți crea și actualiza task-uri în Notion și rânduri în Sheets când se cere explicit
- La adăugare în Sheets: pune DOAR câmpurile pe care utilizatorul le spune; restul rămân goale
- Folosește parametrul detalii doar pentru câmpurile explicite (format key=value|key=value)
- Confirmă clar orice modificare făcută în Notion sau Sheets
- Răspunde în română, empatic și practic
- Dacă Andrei împărtășește o idee nouă, sugerează pași concreți de implementare (nu doar validare)
- Nu genera briefing complet decât dacă se cere explicit
- Dacă există secțiunea „Rezultate căutare web”, utilizatorul are deja linkurile — oferă sugestii concrete din conținutul citit și citează sursele""",
                expected_output=(
                    "Răspuns conversațional util, cu acțiuni concrete "
                    "dacă s-au făcut modificări în Notion."
                ),
                agent=self.agents["ceo"],
            ),
        ]

    def create_custom_tasks(self, user_query: str) -> list[Task]:
        ctx = self._build_context(user_query)
        return [
            Task(
                description=f"""{ctx}
Procesează cererea lui Andrei și coordonează echipa de agenți.
Oferă răspuns integrat care acoperă toate dimensiunile relevante.""",
                expected_output="Răspuns complet, structurat, acționabil în română.",
                agent=self.agents["ceo"],
            ),
            Task(
                description=f"Contribuie cu perspectiva ta de expert la: {user_query}",
                expected_output="Contribuție specializată relevantă.",
                agent=self.agents["content"],
            ),
            Task(
                description=f"Verifică implicații task/client pentru: {user_query}",
                expected_output="Update task-uri și deadlines relevante.",
                agent=self.agents["task_manager"],
            ),
            Task(
                description=f"Evaluează impact familie/echilibru pentru: {user_query}",
                expected_output="Perspectivă wellbeing și recomandări.",
                agent=self.agents["family"],
            ),
            Task(
                description=f"Oferă reflecție profundă despre: {user_query}",
                expected_output="Reflecție și întrebări pentru procesare personală.",
                agent=self.agents["reflector"],
            ),
        ]

    def _agents_for_mode(self, mode: str) -> list:
        if mode == "idea":
            return [create_idea_mode_agent()]
        return list(self.agents.values())

    def _tasks_for_mode(
        self,
        mode: str,
        query: str,
        conversation_context: str = "",
        web_search_context: str = "",
    ) -> list[Task]:
        if mode == "daily":
            return self.create_daily_briefing_tasks()
        if mode == "weekly":
            return self.create_weekly_review_tasks()
        if mode == "chat":
            return self.create_chat_tasks(
                query or "Salut", conversation_context, web_search_context
            )
        if mode == "idea":
            return self.create_idea_tasks(query or "Idee nouă")
        return self.create_custom_tasks(query or "Status general")

    def run(
        self,
        mode: str = "custom",
        query: str = "",
        conversation_context: str = "",
        web_search_context: str = "",
    ) -> str:
        tasks = self._tasks_for_mode(
            mode, query, conversation_context, web_search_context
        )
        agents = self._agents_for_mode(mode)

        crew = Crew(
            agents=agents,
            tasks=tasks,
            process=Process.sequential,
            verbose=True,
            memory=False,
        )

        logger.info("crew_starting", mode=mode, query=query[:100] if query else "")
        result = crew.kickoff()
        output = str(result)

        self.memory.store(
            content=f"[{mode}] {query or 'scheduled'}: {output[:500]}",
            agent="crew",
            category=mode,
        )
        logger.info("crew_completed", mode=mode)
        if mode == "daily":
            output = append_to_daily_briefing(output)
        if mode == "idea":
            output = self._append_idea_notion_save(output, query or "")
        return output

    def _append_idea_notion_save(self, output: str, idea_text: str) -> str:
        try:
            page = NotionClient().save_idea_suggestion(idea_text=idea_text, plan_text=output)
        except Exception as e:
            logger.warning("idea_notion_save_failed", error=str(e))
            return f"{output}\n\n_(Notion: salvare eșuată — {e})_"
        if not page:
            return output
        title = NotionClient.extract_idea_title(idea_text)
        return f"{output}\n\n✅ **Salvat în Notion → Ideas:** {title}"


def run_crew(
    query: str = "",
    mode: str = "custom",
    conversation_context: str = "",
    web_search_context: str = "",
) -> str:
    return AndreiCrew().run(
        mode=mode,
        query=query,
        conversation_context=conversation_context,
        web_search_context=web_search_context,
    )