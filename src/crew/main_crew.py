"""Main CrewAI crew orchestrating all 5 agents."""

from crewai import Crew, Process, Task

from src.agents.definitions import create_all_agents
from src.integrations.memory import MemoryStore
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
Răspunde în română, concis, empatic.""",
                expected_output="Briefing zilnic structurat cu priorități, calendar, alerte și sugestie familie.",
                agent=self.agents["ceo"],
            ),
            Task(
                description="""Pe baza briefing-ului CEO, verifică content pipeline-ul:
- Idei noi sau postări planificate
- Sugestie rapidă de conținut pentru azi/mâine dacă e cazul""",
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

    def run(self, mode: str = "custom", query: str = "") -> str:
        if mode == "daily":
            tasks = self.create_daily_briefing_tasks()
        elif mode == "weekly":
            tasks = self.create_weekly_review_tasks()
        else:
            tasks = self.create_custom_tasks(query or "Status general")

        crew = Crew(
            agents=list(self.agents.values()),
            tasks=tasks,
            process=Process.sequential,
            verbose=True,
            memory=True,
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
        return output


def run_crew(query: str = "", mode: str = "custom") -> str:
    return AndreiCrew().run(mode=mode, query=query)