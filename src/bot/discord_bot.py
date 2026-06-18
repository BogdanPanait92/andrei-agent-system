"""Discord bot for two-way chat with the Andrei AI crew."""

from __future__ import annotations

import asyncio
import re
from typing import TYPE_CHECKING

import discord

from src.bot.conversation_context import ConversationContext
from src.bot.save_intent import is_save_to_notion_request
from src.bot.web_search_intent import parse_web_search_query
from src.crew.main_crew import run_crew
from src.integrations.content_briefing import ContentBriefingService
from src.integrations.ideas_list import IdeasListService
from src.integrations.notion import NotionClient
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
- `ce taskuri am azi?`
- `adaugă task: sună clientul X până vineri`
- `marchează task-ul Y ca Done`
- `ce am în calendar azi?`
- `adaugă partener: ONG X` (doar numele — restul coloanelor rămân goale)
- `adaugă partener: ONG X, locație Cluj, contact Ana`
- `adaugă material: Clip vlog, link https://..., assignat Maria`
- `idee: podcast cu voluntarii ACP` — plan de implementare (salvat automat în Notion Ideas)
- după o discuție: `da, salvează asta în Notion` — salvează ultima conversație ca idee Draft
- `caută: trenduri content 2026` sau `caută pe net caru cu bere` — linkuri + sugestii din pagini citite

Comenzi rapide:
- `help` / `ajutor` — această listă
- `daily` — briefing zilnic (include Content Creation)
- `content` — doar Content Creation (lipsuri + gata de postat)
- `weekly` — review săptămânal

Folosesc Notion, Google Sheets, Calendar și memoria agentului pentru răspunsuri live."""


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

    def _extract_idea_text(self, query: str) -> str | None:
        lowered = query.strip().lower()
        prefixes = (
            "idee:",
            "idea:",
            "idee+salveaza:",
            "idee+salvează:",
            "idee + salveaza:",
            "idee + salvează:",
            "am o idee:",
            "am o idee ",
            "o idee:",
        )
        for prefix in prefixes:
            if lowered.startswith(prefix):
                return query[len(prefix) :].strip() or None
        triggers = (
            "cum as implementa",
            "cum aș implementa",
            "sugestii de implementare",
            "sugestii implementare",
            "plan de implementare",
            "cum implementez",
        )
        if any(t in lowered for t in triggers) and len(query) > 20:
            return query.strip()
        return None

    def _resolve_mode_and_query(self, query: str) -> tuple[str, str]:
        normalized = query.strip().lower()
        if normalized in {"help", "ajutor", "?"}:
            return "help", query
        if normalized == "daily":
            return "daily", "daily briefing complet"
        if normalized in {"content", "content creation", "content briefing"}:
            return "content", ""
        idea_text = self._extract_idea_text(query)
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
        return "chat", query

    async def on_ready(self) -> None:
        logger.info(
            "discord_bot_ready",
            user=str(self.user),
            channels=len(self.allowed_channels),
        )

    async def on_message(self, message: discord.Message) -> None:
        if message.author.bot or not self.user:
            return
        if not self._is_authorized(message):
            return

        query = self._extract_query(message)
        if not query:
            return

        if message.channel.id in self._busy_channels:
            await message.reply("Încă procesez mesajul anterior — un moment.")
            return

        mode, resolved_query = self._resolve_mode_and_query(query)
        if mode == "help":
            await message.reply(HELP_TEXT)
            return
        if mode == "content":
            self._busy_channels.add(message.channel.id)
            try:
                await self._handle_content_briefing(message)
            finally:
                self._busy_channels.discard(message.channel.id)
            return
        if mode == "ideas_list":
            self._busy_channels.add(message.channel.id)
            try:
                await self._handle_ideas_list(message, resolved_query)
            finally:
                self._busy_channels.discard(message.channel.id)
            return
        if is_save_to_notion_request(query):
            self._busy_channels.add(message.channel.id)
            try:
                await self._handle_save_to_notion(message)
            finally:
                self._busy_channels.discard(message.channel.id)
            return
        if mode == "web_search":
            self._busy_channels.add(message.channel.id)
            try:
                await self._handle_web_search(message, resolved_query)
            finally:
                self._busy_channels.discard(message.channel.id)
            return

        self._busy_channels.add(message.channel.id)
        try:
            await self._handle_agent_request(message, resolved_query, mode)
        finally:
            self._busy_channels.discard(message.channel.id)

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
        self._conversation.add(message.channel.id, message.content.strip(), full_reply)
        for chunk in NotifierMixin.split_message(suggestions, max_len=DISCORD_MAX_LEN):
            await message.reply(chunk)

    async def _handle_save_to_notion(self, message: discord.Message) -> None:
        channel: Messageable = message.channel
        exchange = self._conversation.get_last(message.channel.id)
        if not exchange:
            await message.reply(
                "Nu am o conversație anterioară în acest canal. "
                "Spune-mi ideea cu `idee: ...` sau descrie ce vrei salvat."
            )
            return

        async with channel.typing():
            try:
                result = await asyncio.to_thread(self._save_exchange_to_notion, exchange)
            except Exception as e:
                logger.error("discord_save_to_notion_failed", error=str(e))
                await message.reply(f"Eroare la salvare în Notion: {e}")
                return

        self._conversation.add(message.channel.id, message.content.strip(), result)
        for chunk in NotifierMixin.split_message(result, max_len=DISCORD_MAX_LEN):
            await message.reply(chunk)

    @staticmethod
    def _save_exchange_to_notion(exchange) -> str:
        page = NotionClient().save_idea_suggestion(
            idea_text=exchange.user,
            plan_text=exchange.assistant,
            source="Discord",
        )
        if not page:
            return "Notion Ideas nu e configurat — nu am putut salva."
        title = NotionClient.extract_idea_title(exchange.user)
        status = NotionClient.extract_text_property(page, "status") or "Draft"
        return (
            f"✅ **Salvat în Notion → Ideas** (status: {status})\n"
            f"**Titlu:** {title}\n"
            f"_Am salvat întrebarea ta și recomandările mele din conversația anterioară._"
        )

    async def _handle_ideas_list(self, message: discord.Message, status: str) -> None:
        channel: Messageable = message.channel
        async with channel.typing():
            try:
                result = await asyncio.to_thread(IdeasListService().run, status)
            except Exception as e:
                logger.error("discord_ideas_list_failed", error=str(e))
                await message.reply(f"Eroare la citirea ideilor: {e}")
                return
        self._conversation.add(message.channel.id, message.content.strip(), str(result))
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

        self._conversation.add(message.channel.id, query, str(result))
        for chunk in NotifierMixin.split_message(str(result), max_len=DISCORD_MAX_LEN):
            await message.reply(chunk)


def run_discord_bot() -> None:
    token = settings.discord_bot_token.strip()
    if not token:
        raise ValueError("DISCORD_BOT_TOKEN not configured")

    bot = AndreiDiscordBot()
    bot.run(token, log_handler=None)