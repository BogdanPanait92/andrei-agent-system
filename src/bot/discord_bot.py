"""Discord bot for two-way chat with the Andrei AI crew."""

from __future__ import annotations

import asyncio
import re
from typing import TYPE_CHECKING

import discord

from src.bot.conversation_context import ConversationContext
from src.bot.family_intent import extract_family_title, parse_family_request
from src.bot.filmed_intent import (
    deserialize_filmed_request,
    parse_filmed_location,
    serialize_filmed_request,
)
from src.bot.ajut_intent import extract_ajut_title, parse_ajut_request
from src.bot.idea_intent import is_direct_idea_save_request, parse_idea_request
from src.bot.notion_workspace_intent import mentions_non_ideas_notion_workspace
from src.bot.job_intent import extract_job_title, parse_job_request
from src.bot.research_intent import (
    is_research_exit,
    parse_research_query,
    wants_save_to_ideas_with_research,
)
from src.bot.save_intent import (
    is_save_previous_exchange_request,
    parse_save_ideas_hint,
)
from src.bot.voice_message import get_voice_attachment
from src.bot.voiceover_intent import parse_voiceover_request
from src.bot.web_search_intent import parse_web_search_query
from src.crew.main_crew import run_crew
from src.integrations.content_briefing import ContentBriefingService
from src.integrations.idea_voiceover import IdeaVoiceoverService
from src.integrations.ideas_list import IdeasListService
from src.jobs.auto_voiceover import run_auto_voiceover
from src.jobs.task_reminder import (
    is_task_reminder_window,
    run_task_reminder,
    task_reminder_dm_user_ids,
)
from src.integrations.notion import NotionClient
from src.integrations.voice_transcription import VoiceTranscriptionService
from src.integrations.web_search import WebSearchService
from src.graph.workflow import run_workflow
from src.integrations.notifier_base import NotifierMixin
from src.utils.config import settings
from src.utils.logging import get_logger

if TYPE_CHECKING:
    from discord.abc import Messageable

logger = get_logger(__name__)

DISCORD_MAX_LEN = 2000

HELP_TEXT = """**Andrei AI — comenzi**

Scrie direct în acest canal sau menționează-mă oriunde:
- `ce am în Family & Administrative azi?`
- `adaugă: sună școala până vineri` (Family & Administrative)
- `marchează X ca Done` (Family & Administrative)
- `ce am în calendar azi?`
- `adaugă partener: ONG X` — Ajut Cum Pot în Notion
- `tot legat de ajut cum pot, ...` / `ACP, ...` / `pune în ACP: ...` — notă Ajut Cum Pot
- `adaugă postare: Clip vlog` / `adaugă în posting plan: X, oras=București, prioritate=p1`
- `am filmat la Momo` / `am filmat la X, due date 2026-06-25` — linie nouă în Posting Plan
- `pune în tabul job: ...` / `tot pentru job, ...` / `legat de job, notesc că ...` — notă în Notion Job
- `idee: podcast cu voluntarii ACP` — 2 variante voice-over viral (max 90s) + salvare Notion Ideas
- sau natural: „notează/adaugă la idei...”, „pune în idei...” — research + salvare Notion Ideas (cât timp research e activ)
- după o discuție: `da, salvează asta în Notion` — salvează ultima conversație ca idee Draft
- `caută pe net ...` / `vreau să cauți pe net despre ...` — linkuri + sugestii
- `research` / `grok` / `vreau să faci research despre ...` — chat informativ ca Grok
- combinat: `...research despre X și adaugă la idei` / `...și să creez o pagină` — research + salvare Notion Ideas
- `voiceover: platon timp` / `generează voice-over pe ideea X` — 2 variante pe o idee **deja în Notion**
- **Auto:** ideile Draft fără voice-over primesc 2 variante automat în fundal
- **mesaj vocal** în canalul permis — transcriere automată (Whisper) + același flux ca textul

Mod **research** e activ implicit pentru întrebări generale și **Idei**. Pentru Family, Posting Plan, Job, ACP, Calendar etc. folosesc agentul cu Notion — fără research. `research stop` / `research` pentru control manual.

Comenzi rapide:
- `help` / `ajutor` — această listă
- `daily` — briefing zilnic (include Content Creation)
- `content` — doar Content Creation (lipsuri + gata de postat)
- `weekly` — review săptămânal

Folosesc Notion (inclusiv Posting Plan), Calendar și memoria agentului pentru răspunsuri live."""


def _parse_id_list(raw: str) -> set[int]:
    ids: set[int] = set()
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            ids.add(int(part))
    return ids


class AndreiDiscordBot(discord.Client):
    def __init__(self) -> None:
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(intents=intents)
        self.allowed_channels = _parse_id_list(settings.discord_allowed_channel_ids)
        self.allowed_users = _parse_id_list(settings.discord_allowed_user_ids)
        self._busy_channels: set[int] = set()
        self._conversation = ConversationContext()
        self._active_query: str | None = None
        self._research_disabled_channels: set[int] = set()
        self._auto_voiceover_busy = False
        self._auto_voiceover_started = False
        self._task_reminder_busy = False
        self._task_reminder_started = False

    def _is_authorized(self, message: discord.Message) -> bool:
        if self.allowed_users and message.author.id not in self.allowed_users:
            return False
        if isinstance(message.channel, discord.DMChannel):
            return True
        if self.allowed_channels:
            return message.channel.id in self.allowed_channels
        return bool(message.guild)

    def _extract_query(self, message: discord.Message) -> str | None:
        content = message.content.strip()
        if not content:
            return None

        mentioned = self.user and self.user in message.mentions
        prefixed = content.lower().startswith("!andrei ")
        in_allowed_channel = message.channel.id in self.allowed_channels

        if mentioned:
            content = re.sub(r"<@!?\d+>", "", content).strip()

        if prefixed:
            content = content[8:].strip()

        if in_allowed_channel or mentioned or prefixed or isinstance(message.channel, discord.DMChannel):
            return content or None

        return None

    def _user_line(self, message: discord.Message, fallback: str = "") -> str:
        return message.content.strip() or self._active_query or fallback

    def _accepts_voice_only(self, message: discord.Message) -> bool:
        if isinstance(message.channel, discord.DMChannel):
            return True
        if self.allowed_channels:
            return message.channel.id in self.allowed_channels
        return bool(message.guild)

    def _extract_idea_text(self, query: str) -> str | None:
        return parse_idea_request(query)

    def _is_priority_command(self, query: str) -> bool:
        normalized = query.strip().lower()
        if normalized in {"help", "ajutor", "?", "daily", "weekly"}:
            return True
        if normalized in {"content", "content creation", "content briefing"}:
            return True
        if is_direct_idea_save_request(query):
            return True
        if IdeasListService.parse_status_from_query(query) is not None:
            return True
        if parse_web_search_query(query) and settings.enable_web_search:
            return True
        if parse_voiceover_request(query) is not None:
            return True
        if parse_filmed_location(query) is not None:
            return True
        if parse_job_request(query) is not None:
            return True
        if parse_family_request(query) is not None:
            return True
        if parse_ajut_request(query) is not None:
            return True
        if is_save_previous_exchange_request(query):
            return True
        if mentions_non_ideas_notion_workspace(query):
            return True
        if any(
            phrase in normalized
            for phrase in (
                "briefing content",
                "content creation briefing",
                "ce lipseste la content",
                "ce lipsește la content",
                "gata de postat",
            )
        ):
            return True
        return False

    def _research_enabled(self, channel_id: int | None) -> bool:
        if not settings.enable_research_mode:
            return False
        if channel_id is None:
            return True
        return channel_id not in self._research_disabled_channels

    def _resolve_mode_and_query(
        self, query: str, channel_id: int | None = None
    ) -> tuple[str, str]:
        normalized = query.strip().lower()
        if normalized in {"help", "ajutor", "?"}:
            return "help", query
        if is_research_exit(query):
            if channel_id is not None:
                self._research_disabled_channels.add(channel_id)
            return "research_exit", query
        if normalized in {"research", "research start", "porneste research", "pornește research"}:
            if channel_id is not None:
                self._research_disabled_channels.discard(channel_id)
            return "research_enter", query
        if normalized == "daily":
            return "daily", "daily briefing complet"
        if normalized in {"content", "content creation", "content briefing"}:
            return "content", ""
        filmed_req = parse_filmed_location(query)
        if filmed_req is not None:
            return "filmed_location", serialize_filmed_request(filmed_req)
        ajut_body = parse_ajut_request(query)
        if ajut_body is not None:
            return "ajut_note", ajut_body
        job_body = parse_job_request(query)
        if job_body is not None:
            return "job_note", job_body
        family_body = parse_family_request(query)
        if family_body is not None:
            return "family_note", family_body
        research_query = parse_research_query(query)
        if research_query is not None and settings.enable_research_mode:
            if channel_id is not None:
                self._research_disabled_channels.discard(channel_id)
            if not research_query:
                return "research_enter", query
            if wants_save_to_ideas_with_research(query):
                return "research_save", research_query
            return "research", research_query
        if is_save_previous_exchange_request(query):
            return "save_ideas", query
        idea_text = self._extract_idea_text(query)
        if idea_text and is_direct_idea_save_request(query):
            if settings.enable_research_mode and self._research_enabled(channel_id):
                return "research_save", idea_text
            return "idea_note", idea_text
        voiceover_req = parse_voiceover_request(query)
        if voiceover_req is not None:
            idea_ref, status = voiceover_req
            resolved = f"{status}|||{idea_ref}" if status else idea_ref
            return "idea_voiceover", resolved
        if idea_text:
            return "idea", idea_text
        ideas_status = IdeasListService.parse_status_from_query(query)
        if ideas_status is not None:
            return "ideas_list", ideas_status
        web_query = parse_web_search_query(query)
        if web_query and settings.enable_web_search:
            return "web_search", web_query
        if normalized == "weekly":
            return "weekly", "weekly review duminică"
        if any(
            phrase in normalized
            for phrase in (
                "briefing content",
                "content creation briefing",
                "ce lipseste la content",
                "ce lipsește la content",
                "gata de postat",
            )
        ):
            return "content", query
        if mentions_non_ideas_notion_workspace(query):
            return "chat", query
        if self._research_enabled(channel_id):
            return "research", query
        return "chat", query

    async def on_ready(self) -> None:
        logger.info(
            "discord_bot_ready",
            user=str(self.user),
            channels=len(self.allowed_channels),
            auto_voiceover=settings.enable_auto_voiceover,
            task_reminder=settings.enable_task_reminder,
            research_default=settings.enable_research_mode,
        )
        if settings.enable_auto_voiceover and not self._auto_voiceover_started:
            self._auto_voiceover_started = True
            asyncio.create_task(self._auto_voiceover_loop())
        if (
            settings.enable_task_reminder
            and settings.task_reminder_discord
            and not self._task_reminder_started
        ):
            self._task_reminder_started = True
            asyncio.create_task(self._task_reminder_loop())

    async def _auto_voiceover_loop(self) -> None:
        await self.wait_until_ready()
        initial_delay = 90
        interval_seconds = max(5, settings.auto_voiceover_interval_minutes) * 60
        await asyncio.sleep(initial_delay)

        while not self.is_closed():
            if not self._auto_voiceover_busy:
                self._auto_voiceover_busy = True
                try:
                    result = await asyncio.to_thread(run_auto_voiceover)
                    if settings.auto_voiceover_notify_discord and result.get("processed"):
                        await self._notify_auto_voiceover(result)
                except Exception as e:
                    logger.error("auto_voiceover_loop_failed", error=str(e))
                finally:
                    self._auto_voiceover_busy = False
            await asyncio.sleep(interval_seconds)

    async def _notify_auto_voiceover(self, result: dict) -> None:
        if not self.allowed_channels:
            return
        channel_id = next(iter(self.allowed_channels))
        channel = self.get_channel(channel_id)
        if channel is None:
            return

        titles = result.get("processed") or []
        remaining = result.get("pending_remaining", 0)
        lines = [
            "🎙️ **Voice-over auto** — am generat 2 variante pentru:",
            "",
            *[f"• {title}" for title in titles],
        ]
        if remaining:
            lines.append(f"\n_{remaining} idei Draft încă fără voice-over — le procesez la următorul ciclu._")
        errors = result.get("errors") or []
        if errors:
            lines.append(f"\n⚠️ Erori: {len(errors)} idee(i) — verifică logurile.")

        text = "\n".join(lines)
        for chunk in NotifierMixin.split_message(text, max_len=DISCORD_MAX_LEN):
            await channel.send(chunk)

    async def _task_reminder_loop(self) -> None:
        await self.wait_until_ready()
        interval_seconds = max(1, settings.task_reminder_interval_hours) * 3600
        await asyncio.sleep(120)

        while not self.is_closed():
            if not self._task_reminder_busy:
                self._task_reminder_busy = True
                try:
                    if not is_task_reminder_window():
                        continue
                    result = await asyncio.to_thread(run_task_reminder, send=False)
                    if result.get("status") != "ok":
                        continue
                    message = result.get("message")
                    if message:
                        await self._notify_task_reminder(message)
                except Exception as e:
                    logger.error("task_reminder_loop_failed", error=str(e))
                finally:
                    self._task_reminder_busy = False
            await asyncio.sleep(interval_seconds)

    async def _notify_task_reminder(self, text: str) -> None:
        chunks = NotifierMixin.split_message(text, max_len=DISCORD_MAX_LEN)

        if settings.task_reminder_discord_dm:
            dm_ids = task_reminder_dm_user_ids()
            for user_id in dm_ids:
                try:
                    user = await self.fetch_user(int(user_id))
                    dm = user.dm_channel or await user.create_dm()
                    for chunk in chunks:
                        await dm.send(chunk)
                except Exception as e:
                    logger.error(
                        "task_reminder_discord_dm_failed",
                        user_id=user_id,
                        error=str(e),
                    )
            if dm_ids:
                return

        if not self.allowed_channels:
            return
        channel_id = next(iter(self.allowed_channels))
        channel = self.get_channel(channel_id)
        if channel is None:
            return
        for chunk in chunks:
            await channel.send(chunk)

    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or not self.user:
            return
        if not self._is_authorized(message):
            return

        query = self._extract_query(message)
        if not query:
            voice_attachment = get_voice_attachment(message)
            if (
                voice_attachment
                and settings.enable_discord_voice
                and self._accepts_voice_only(message)
            ):
                if message.channel.id in self._busy_channels:
                    await message.reply("Încă procesez mesajul anterior — un moment.")
                    return
                self._busy_channels.add(message.channel.id)
                try:
                    await self._handle_voice_message(message, voice_attachment)
                finally:
                    self._busy_channels.discard(message.channel.id)
            return

        if message.channel.id in self._busy_channels:
            await message.reply("Încă procesez mesajul anterior — un moment.")
            return

        self._busy_channels.add(message.channel.id)
        try:
            await self._route_and_respond(message, query)
        finally:
            self._busy_channels.discard(message.channel.id)

    async def _route_and_respond(self, message: discord.Message, query: str) -> None:
        mode, resolved_query = self._resolve_mode_and_query(
            query, message.channel.id
        )
        if mode == "help":
            await message.reply(HELP_TEXT)
            return
        if mode == "research_exit":
            await message.reply(
                "Am oprit modul **research** în acest canal — răspunsurile merg acum la agentul complet.\n"
                "Scrie `research` sau `research: întrebarea ta` ca să revii la research."
            )
            return
        if mode == "research_enter":
            await message.reply(
                "Mod **research** activ — ca Grok/ChatGPT, cu research web automat.\n"
                "Întreabă direct (fără prefix) sau `research stop` pentru agentul complet."
            )
            return
        if mode == "content":
            await self._handle_content_briefing(message)
            return
        if mode == "ideas_list":
            await self._handle_ideas_list(message, resolved_query)
            return
        if mode == "idea_voiceover":
            await self._handle_idea_voiceover(message, resolved_query)
            return
        if mode == "filmed_location":
            await self._handle_filmed_location(message, resolved_query)
            return
        if mode == "ajut_note":
            await self._handle_ajut_note(message, resolved_query)
            return
        if mode == "job_note":
            await self._handle_job_note(message, resolved_query)
            return
        if mode == "family_note":
            await self._handle_family_note(message, resolved_query)
            return
        if mode == "save_ideas":
            await self._handle_save_to_notion(message, resolved_query)
            return
        if mode == "idea_note":
            await self._handle_idea_note(message, resolved_query)
            return
        if mode == "web_search":
            await self._handle_web_search(message, resolved_query)
            return
        if mode == "research":
            await self._handle_research_chat(message, resolved_query)
            return
        if mode == "research_save":
            await self._handle_research_chat(
                message, resolved_query, save_to_ideas=True
            )
            return
        await self._handle_agent_request(message, resolved_query, mode)

    async def _handle_voice_message(
        self,
        message: discord.Message,
        attachment: discord.Attachment,
    ) -> None:
        channel: Messageable = message.channel
        max_duration = settings.discord_voice_max_duration_seconds
        if attachment.duration is not None and attachment.duration > max_duration:
            await message.reply(
                f"Mesajul vocal e prea lung (max {max_duration}s). "
                "Încearcă un mesaj mai scurt."
            )
            return
        if attachment.size and attachment.size > settings.discord_voice_max_bytes:
            await message.reply("Fișierul vocal e prea mare pentru transcriere.")
            return

        async with channel.typing():
            try:
                audio_bytes = await attachment.read()
                transcribed = await asyncio.to_thread(
                    VoiceTranscriptionService().transcribe,
                    audio_bytes,
                    attachment.filename or "voice-message.ogg",
                )
            except Exception as e:
                logger.error("discord_voice_transcription_failed", error=str(e))
                await message.reply(f"Nu am putut transcrie mesajul vocal: {e}")
                return

        await message.reply(f"🎤 **Am înțeles:** {transcribed}")
        self._active_query = transcribed
        try:
            await self._route_and_respond(message, transcribed)
        finally:
            self._active_query = None

    async def _handle_research_chat(
        self,
        message: discord.Message,
        research_query: str,
        *,
        save_to_ideas: bool = False,
    ) -> None:
        channel: Messageable = message.channel
        conv_ctx = self._conversation.format_for_prompt(message.channel.id)
        service = WebSearchService()

        status_text = (
            "🔬 Research + 2 variante voice-over — pregătesc răspunsul..."
            if save_to_ideas
            else "🔬 Caut informații și pregătesc răspunsul..."
        )
        status = await message.reply(status_text)
        web_ctx = ""
        if settings.enable_web_search:
            try:
                results = await asyncio.to_thread(service.search, research_query)
                enriched = await asyncio.to_thread(
                    service.enrich_with_page_content, results
                )
                web_ctx = service.format_for_research_prompt(enriched)
            except Exception as e:
                logger.warning(
                    "discord_research_web_failed",
                    error=str(e),
                    query=research_query[:80],
                )
                web_ctx = (
                    "--- Research web ---\n"
                    f"Căutarea web a eșuat ({e}). "
                    "Răspunde din cunoștințele tale generale."
                )

        async with channel.typing():
            try:
                crew_mode = "research_save" if save_to_ideas else "research"
                result = await asyncio.to_thread(
                    run_crew,
                    query=research_query,
                    mode=crew_mode,
                    conversation_context=conv_ctx,
                    web_search_context=web_ctx,
                )
            except Exception as e:
                logger.error("discord_research_crew_failed", error=str(e))
                await status.edit(content=f"Eroare la research: {e}")
                return

        reply = str(result)
        if save_to_ideas:
            try:
                page = await asyncio.to_thread(
                    self._save_research_to_notion,
                    research_query,
                    reply,
                )
            except Exception as e:
                logger.error("discord_research_save_failed", error=str(e))
                reply += f"\n\n_(Nu am putut salva în Notion Ideas: {e})_"
            else:
                if page:
                    title = NotionClient.extract_idea_title(research_query)
                    status_val = (
                        NotionClient.extract_text_property(page, "status") or "Draft"
                    )
                    reply += (
                        f"\n\n✅ **Salvat în Notion → Ideas** (status: {status_val})\n"
                        f"**Titlu:** {title}\n"
                        f"_Research-ul de mai sus e în corpul paginii._"
                    )
                else:
                    reply += "\n\n_(Notion Ideas nu e configurat — research nesalvat.)_"

        self._conversation.add(
            message.channel.id, self._user_line(message, research_query), reply
        )
        try:
            await status.delete()
        except discord.HTTPException:
            pass
        for chunk in NotifierMixin.split_message(reply, max_len=DISCORD_MAX_LEN):
            await message.reply(chunk)

    @staticmethod
    def _save_research_to_notion(research_query: str, research_text: str):
        return NotionClient().save_idea_suggestion(
            idea_text=research_query,
            plan_text=research_text,
            source="Discord-research",
        )

    async def _handle_web_search(self, message: discord.Message, search_query: str) -> None:
        channel: Messageable = message.channel
        conv_ctx = self._conversation.format_for_prompt(message.channel.id)
        service = WebSearchService()

        try:
            results = await asyncio.to_thread(service.search, search_query)
        except Exception as e:
            logger.error("discord_web_search_failed", error=str(e), query=search_query[:80])
            await message.reply(f"Eroare la căutarea web: {e}")
            return

        links_msg = service.format_links_message(results, search_query)
        for chunk in NotifierMixin.split_message(links_msg, max_len=DISCORD_MAX_LEN):
            await message.reply(chunk)

        async with channel.typing():
            try:
                enriched = await asyncio.to_thread(service.enrich_with_page_content, results)
                web_ctx = service.format_for_prompt(enriched)
            except Exception as e:
                logger.error("discord_web_fetch_failed", error=str(e), query=search_query[:80])
                await message.reply(f"Eroare la citirea paginilor: {e}")
                return

            user_prompt = (
                f"[Căutare web — faza de sugestii]\n"
                f"Termen căutat: {search_query}\n"
                f"Utilizatorul a primit deja linkurile. "
                f"Citește conținutul paginilor și oferă sugestii concrete pentru Andrei."
            )
            try:
                result = await asyncio.to_thread(
                    run_crew,
                    query=user_prompt,
                    mode="chat",
                    conversation_context=conv_ctx,
                    web_search_context=web_ctx,
                )
            except Exception as e:
                logger.error("discord_web_search_crew_failed", error=str(e))
                await message.reply(f"Eroare la generarea sugestiilor: {e}")
                return

        suggestions = f"📋 **Sugestii pe baza surselor:**\n\n{result}"
        full_reply = f"{links_msg}\n\n{suggestions}"
        self._conversation.add(message.channel.id, self._user_line(message, search_query), full_reply)
        for chunk in NotifierMixin.split_message(suggestions, max_len=DISCORD_MAX_LEN):
            await message.reply(chunk)

    async def _handle_save_to_notion(
        self, message: discord.Message, query: str = ""
    ) -> None:
        channel: Messageable = message.channel
        exchange = self._conversation.get_last_substantive(message.channel.id)
        if not exchange:
            await message.reply(
                "Nu am o conversație anterioară în acest canal. "
                "Spune-mi ideea cu `idee: ...` sau descrie ce vrei salvat."
            )
            return

        hint = parse_save_ideas_hint(query) if query else None

        async with channel.typing():
            try:
                result = await asyncio.to_thread(
                    self._save_exchange_to_notion, exchange, hint
                )
            except Exception as e:
                logger.error("discord_save_to_notion_failed", error=str(e))
                await message.reply(f"Eroare la salvare în Notion: {e}")
                return

        for chunk in NotifierMixin.split_message(result, max_len=DISCORD_MAX_LEN):
            await message.reply(chunk)

    @staticmethod
    def _save_exchange_to_notion(exchange, hint: str | None = None) -> str:
        title_source = hint or parse_idea_request(exchange.user) or exchange.user
        page = NotionClient().save_idea_suggestion(
            idea_text=exchange.user,
            plan_text=exchange.assistant,
            source="Discord",
            title=title_source,
        )
        if not page:
            return "Notion Ideas nu e configurat — nu am putut salva."
        title = NotionClient.extract_idea_title(title_source)
        status = NotionClient.extract_text_property(page, "status") or "Draft"
        return (
            f"✅ **Salvat în Notion → Ideas** (status: {status})\n"
            f"**Titlu:** {title}\n"
            f"_Am salvat întrebarea ta și recomandările mele din conversația anterioară._"
        )

    async def _handle_idea_note(self, message: discord.Message, resolved: str) -> None:
        channel: Messageable = message.channel
        idea_text = resolved.strip()

        async with channel.typing():
            try:
                reply = await asyncio.to_thread(self._save_idea_note, idea_text)
            except Exception as e:
                logger.error("discord_idea_note_failed", error=str(e))
                await message.reply(f"Eroare la salvare în Ideas: {e}")
                return

        self._conversation.add(
            message.channel.id, self._user_line(message, idea_text), reply
        )
        for chunk in NotifierMixin.split_message(reply, max_len=DISCORD_MAX_LEN):
            await message.reply(chunk)

    @staticmethod
    def _save_idea_note(idea_text: str) -> str:
        page = NotionClient().save_idea_suggestion(
            idea_text=idea_text,
            plan_text="",
            source="Discord",
        )
        if not page:
            return "Notion Ideas nu e configurat — nu am putut salva."
        title = NotionClient.extract_idea_title(idea_text)
        status = NotionClient.extract_text_property(page, "status") or "Draft"
        return (
            f"✅ **Salvat în Notion → Ideas** (status: {status})\n"
            f"**Titlu:** {title}\n"
            f"_Ideea e în baza de date Ideas._"
        )

    async def _handle_ajut_note(self, message: discord.Message, resolved: str) -> None:
        channel: Messageable = message.channel
        content = resolved.strip()

        async with channel.typing():
            try:
                reply = await asyncio.to_thread(self._save_ajut_note, content)
            except Exception as e:
                logger.error("discord_ajut_note_failed", error=str(e))
                await message.reply(f"Eroare la salvare în Ajut Cum Pot: {e}")
                return

        self._conversation.add(message.channel.id, self._user_line(message, content), reply)
        for chunk in NotifierMixin.split_message(reply, max_len=DISCORD_MAX_LEN):
            await message.reply(chunk)

    @staticmethod
    def _save_ajut_note(content: str) -> str:
        if not settings.notion_ajut_cum_pot_db_id:
            return "Ajut Cum Pot neconfigurat (NOTION_AJUT_CUM_POT_DB_ID)."

        title = extract_ajut_title(content)
        notion = NotionClient()
        page = notion.create_ajut_cum_pot_item(title=title, content=content)
        if not page:
            return "Nu am putut salva în Ajut Cum Pot — verifică NOTION_AJUT_CUM_POT_DB_ID."

        return (
            f"✅ **Salvat în Notion → Ajut Cum Pot**\n"
            f"**Titlu:** {title}\n"
            f"_Detaliile complete sunt în conținutul paginii._"
        )

    async def _handle_family_note(self, message: discord.Message, resolved: str) -> None:
        channel: Messageable = message.channel
        content = resolved.strip()

        async with channel.typing():
            try:
                reply = await asyncio.to_thread(self._save_family_note, content)
            except Exception as e:
                logger.error("discord_family_note_failed", error=str(e))
                await message.reply(f"Eroare la salvare în Family & Administrative: {e}")
                return

        self._conversation.add(message.channel.id, self._user_line(message, content), reply)
        for chunk in NotifierMixin.split_message(reply, max_len=DISCORD_MAX_LEN):
            await message.reply(chunk)

    @staticmethod
    def _save_family_note(content: str) -> str:
        if not settings.notion_family_db_id:
            return "Family & Administrative neconfigurat (NOTION_FAMILY_DB_ID)."

        title = extract_family_title(content)
        notion = NotionClient()
        page = notion.create_family_item(title=title)
        if not page:
            return "Nu am putut salva în Family & Administrative — verifică NOTION_FAMILY_DB_ID."

        return (
            f"✅ **Salvat în Notion → Family & Administrative**\n"
            f"**Titlu:** {title}\n"
            f"_Intrarea e în baza de date, status To Do._"
        )

    async def _handle_job_note(self, message: discord.Message, resolved: str) -> None:
        channel: Messageable = message.channel
        content = resolved.strip()

        async with channel.typing():
            try:
                reply = await asyncio.to_thread(self._save_job_note, content)
            except Exception as e:
                logger.error("discord_job_note_failed", error=str(e))
                await message.reply(f"Eroare la salvare în Job: {e}")
                return

        self._conversation.add(message.channel.id, self._user_line(message, content), reply)
        for chunk in NotifierMixin.split_message(reply, max_len=DISCORD_MAX_LEN):
            await message.reply(chunk)

    @staticmethod
    def _save_job_note(content: str) -> str:
        if not settings.notion_job_db_id:
            return "Job neconfigurat (NOTION_JOB_DB_ID)."

        title = extract_job_title(content)
        notion = NotionClient()
        page = notion.save_job_entry(title=title, content=content)
        if not page:
            return "Nu am putut salva în Job — verifică NOTION_JOB_DB_ID."

        return (
            f"✅ **Salvat în Notion → Job**\n"
            f"**Titlu:** {title}\n"
            f"_Nota e în baza de date Job, cu data de azi._"
        )

    async def _handle_filmed_location(self, message: discord.Message, resolved: str) -> None:
        channel: Messageable = message.channel
        req = deserialize_filmed_request(resolved)

        async with channel.typing():
            try:
                reply = await asyncio.to_thread(self._add_filmed_to_posting_plan, req)
            except Exception as e:
                logger.error("discord_filmed_location_failed", error=str(e))
                await message.reply(f"Eroare la adăugare în Posting Plan: {e}")
                return

        self._conversation.add(message.channel.id, self._user_line(message, req.location), reply)
        for chunk in NotifierMixin.split_message(reply, max_len=DISCORD_MAX_LEN):
            await message.reply(chunk)

    @staticmethod
    def _add_filmed_to_posting_plan(req) -> str:
        notion = NotionClient()
        if not settings.notion_posting_plan_db_id:
            return "Posting Plan neconfigurat (NOTION_POSTING_PLAN_DB_ID)."

        existing = notion.find_posting_plan_by_title(req.location)
        if existing:
            if req.due_date:
                notion.append_posting_plan_scheduled_date(existing["id"], req.due_date)
                return (
                    f"✅ **Posting Plan actualizat** — **{req.location}**\n"
                    f"Dată planificată adăugată în pagină: {req.due_date}"
                )
            if req.oras:
                notion.update_posting_plan_item(existing["id"], oras=req.oras)
                return (
                    f"✅ **Posting Plan actualizat** — **{req.location}**\n"
                    f"**Oraș:** {req.oras}"
                )
            return (
                f"**{req.location}** există deja în Posting Plan. "
                "Spune o dată dacă vrei să o notez în pagină."
            )

        notion.create_posting_plan_item(
            title=req.location,
            oras=req.oras,
            status="Planned",
            scheduled_date=req.due_date,
        )
        oras_line = f"\n**Oraș:** {req.oras}" if req.oras else ""
        date_line = f"\n**Dată planificată:** {req.due_date}" if req.due_date else ""
        return (
            f"✅ **Adăugat în Notion → Posting Plan**\n"
            f"**Titlu:** {req.location}\n"
            f"**Status:** Planned{oras_line}{date_line}"
        )

    async def _handle_idea_voiceover(self, message: discord.Message, resolved: str) -> None:
        channel: Messageable = message.channel
        if "|||" in resolved:
            status, idea_ref = resolved.split("|||", 1)
        else:
            status, idea_ref = None, resolved

        async with channel.typing():
            try:
                result = await asyncio.to_thread(
                    IdeaVoiceoverService().run,
                    idea_ref,
                    status,
                )
            except Exception as e:
                logger.error("discord_idea_voiceover_failed", error=str(e))
                await message.reply(f"Eroare la voice-over: {e}")
                return

        self._conversation.add(message.channel.id, self._user_line(message, idea_ref), str(result))
        for chunk in NotifierMixin.split_message(str(result), max_len=DISCORD_MAX_LEN):
            await message.reply(chunk)

    async def _handle_ideas_list(self, message: discord.Message, status: str) -> None:
        channel: Messageable = message.channel
        async with channel.typing():
            try:
                result = await asyncio.to_thread(IdeasListService().run, status)
            except Exception as e:
                logger.error("discord_ideas_list_failed", error=str(e))
                await message.reply(f"Eroare la citirea ideilor: {e}")
                return
        self._conversation.add(message.channel.id, self._user_line(message, status), str(result))
        for chunk in NotifierMixin.split_message(str(result), max_len=DISCORD_MAX_LEN):
            await message.reply(chunk)

    async def _handle_content_briefing(self, message: discord.Message) -> None:
        channel: Messageable = message.channel
        async with channel.typing():
            try:
                result = await asyncio.to_thread(ContentBriefingService().run)
            except Exception as e:
                logger.error("discord_content_briefing_failed", error=str(e))
                await message.reply(f"Eroare Content Creation: {e}")
                return
        for chunk in NotifierMixin.split_message(str(result), max_len=DISCORD_MAX_LEN):
            await message.reply(chunk)

    async def _handle_agent_request(
        self,
        message: discord.Message,
        query: str,
        mode: str,
    ) -> None:
        channel: Messageable = message.channel
        conv_ctx = self._conversation.format_for_prompt(message.channel.id)
        async with channel.typing():
            try:
                if mode == "daily":
                    result = await asyncio.to_thread(run_workflow, mode="daily", query=query)
                else:
                    result = await asyncio.to_thread(
                        run_crew,
                        query=query,
                        mode=mode,
                        conversation_context=conv_ctx,
                    )
            except Exception as e:
                logger.error("discord_crew_failed", error=str(e))
                await message.reply(f"Eroare la procesare: {e}")
                return

        self._conversation.add(message.channel.id, self._user_line(message, query), str(result))
        for chunk in NotifierMixin.split_message(str(result), max_len=DISCORD_MAX_LEN):
            await message.reply(chunk)


def run_discord_bot() -> None:
    token = settings.discord_bot_token.strip()
    if not token:
        raise ValueError("DISCORD_BOT_TOKEN not configured")

    bot = AndreiDiscordBot()
    bot.run(token, log_handler=None)