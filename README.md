# Andrei AI Agent System

Sistem agentic AI complet în cloud pentru **Andrei** — tată, soț, creator de conținut, inginer IT, fondator **Ajut Cum Pot**.

5 agenți specializați lucrează împreună prin **CrewAI** + **LangGraph**, cu **Grok** ca LLM principal și integrări complete Notion, Google Calendar/Sheets, **Discord bot** (chat bidirecțional), notificări (Telegram/WhatsApp/Discord webhook) și memorie persistentă.

---

## Arhitectură

```
┌─────────────────────────────────────────────────────────────┐
│              Railway.app sau Hostinger VPS (Cloud)          │
├─────────────────────────────────────────────────────────────┤
│  Scheduler (cron)  │  API Server  │  Streamlit Dashboard    │
├─────────────────────────────────────────────────────────────┤
│              LangGraph Workflow Orchestrator                │
├─────────────────────────────────────────────────────────────┤
│                    CrewAI Main Crew                         │
│  ┌────────┐ ┌─────────┐ ┌──────────┐ ┌────────┐ ┌────────┐  │
│  │  CEO   │ │ Content │ │  Task    │ │ Family │ │Reflect │  │
│  │ Agent  │ │ Creator │ │ Manager  │ │Balance │ │  Agent │  │
│  └────────┘ └─────────┘ └──────────┘ └────────┘ └────────┘  │
├─────────────────────────────────────────────────────────────┤
│  Notion │ Google Calendar/Sheets │ Discord Bot │ Telegram/  │
│  WhatsApp/Discord │ Supabase Memory │ Web Search (explicit) │
└─────────────────────────────────────────────────────────────┘
```

### Agenți

| Agent | Rol |
|-------|-----|
| **CEO** | Strategie, prioritizare, briefing zilnic/săptămânal, echilibru Corporație/Creativ/ACP/Familie |
| **Content Creator** | Idei conținut, posting plan, analiză clipuri, pipeline creativ |
| **Task & Client Manager** | Task-uri Notion, deadlines, follow-up clienți |
| **Family & Life Balance** | Echilibru familie, timp de calitate, alerte anti-burnout |
| **Reflector** | Jurnal, reflecții profunde, dilemă stabilitate vs sens |

---

## Quick Start (Local)

### 1. Clonează și configurează

```bash
git clone https://github.com/YOUR_USER/andreia-agent-system.git
cd andreia-agent-system
cp .env.example .env
# Editează .env cu cheile tale
```

### 2. Instalare

```bash
python -m venv venv
# Windows
venv\Scripts\activate
# Linux/Mac
source venv/bin/activate

pip install -r requirements.txt
```

### 3. Setup Supabase (memorie)

1. Creează proiect pe [supabase.com](https://supabase.com)
2. Rulează `scripts/supabase_schema.sql` în SQL Editor
3. Copiază URL + keys în `.env`

### 4. Rulează

```bash
# Daily briefing
python run_daily.py

# Weekly review
python run_weekly.py

# Query custom
python run_crew.py "analizeaza saptamana"
python run_crew.py "ce prioritati am azi?"

# Smart alerts
python run_alerts.py

# Dashboard web
streamlit run src/dashboard/app.py

# Scheduler (cron local)
python src/scheduler.py

# Discord bot (chat interactiv)
python run_discord_bot.py
# Windows:
.\scripts\local_run.ps1 discord-bot
```

---

## Variabile aplicație

```env
USER_NAME=Andrei          # Numele afișat în prompturile agenților
TIMEZONE=Europe/Bucharest
```

---

## Configurare API Keys

### Grok (xAI) — Obligatoriu

1. Cont pe [console.x.ai](https://console.x.ai)
2. Generează API key
3. `.env`: `XAI_API_KEY=xai-...`

### Notion

1. [notion.so/my-integrations](https://www.notion.so/my-integrations) → New integration
2. Copiază Internal Integration Token → `NOTION_API_KEY`
3. Creează databases: Tasks, Ideas, Posting Plan, Ajut Cum Pot, Journal
4. Share fiecare database cu integrarea
5. Copiază Database IDs din URL: `notion.so/workspace/DATABASE_ID?v=...`

**Proprietăți recomandate per database:**

| Database | Proprietăți |
|----------|-------------|
| Tasks | Name (title), Status (select), Priority (select), Due Date (date), Client (text) |
| Ideas | Name (title), Category (select), Notes (text), status (status: Draft, In evaluare, In lucru, Arhivat) |
| Posting Plan | Name (title), Date (date), Platform (select), Status (select) |
| Journal | Name (title), Content (text), Mood (select), Date (date) |

### Google APIs

1. [Google Cloud Console](https://console.cloud.google.com) → New Project
2. Enable APIs: Calendar, Docs, Drive, **Sheets**
3. Create Service Account → Download JSON
4. Share Calendar și fiecare Google Sheet cu email-ul service account (Editor)
5. `.env`: `GOOGLE_CREDENTIALS_JSON={"type":"service_account",...}` (întreg JSON pe o linie)

**Google Sheets (pipeline operațional):**

```env
GOOGLE_SHEET_AJUT_CUM_POT_ID=...
GOOGLE_SHEET_AJUT_TAB=Ajut Cum Pot
GOOGLE_SHEET_EDITOR_PIPELINE_ID=...
GOOGLE_SHEET_EDITOR_TAB=Content Creation
```

Service account-ul **nu poate crea** sheet-uri noi (cotă Drive) — creează-le manual și share-uiește-le.

**Test:**
```powershell
.\scripts\local_run.ps1 google-sheets
```

### Notificări: Telegram, WhatsApp sau Discord

Alege canalul în `.env`:

```env
NOTIFIER_PROVIDER=telegram   # sau whatsapp | discord
```

#### Opțiunea A — Telegram (simplu, gratuit)

1. Mesaj `@BotFather` pe Telegram → `/newbot`
2. Copiază token → `TELEGRAM_BOT_TOKEN`
3. Trimite `/start` botului tău
4. Află chat ID: `https://api.telegram.org/bot<TOKEN>/getUpdates`
5. `.env`: `TELEGRAM_CHAT_ID=...`

#### Opțiunea B — WhatsApp (recomandat dacă folosești WhatsApp zilnic)

Folosește **WhatsApp Business Cloud API** (Meta) — oficial, production-ready.

1. [developers.facebook.com](https://developers.facebook.com) → **Create App** → tip *Business*
2. Adaugă produsul **WhatsApp** → **API Setup**
3. Notează:
   - **Phone number ID** → `WHATSAPP_PHONE_NUMBER_ID`
   - **Temporary access token** (pentru test) sau **Permanent token** (System User în Business Manager)
4. `.env`:
   ```env
   NOTIFIER_PROVIDER=whatsapp
   WHATSAPP_ACCESS_TOKEN=EAAxxxxx
   WHATSAPP_PHONE_NUMBER_ID=123456789012345
   WHATSAPP_RECIPIENT=40722123456
   ```
   `WHATSAPP_RECIPIENT` = numărul lui Andrei în format internațional **fără +** (ex: `40722123456`)

5. **Important — fereastra de 24h:**
   - Mesaje text libere merg doar dacă Andrei a scris business number-ului în ultimele 24h
   - Pentru daily briefing automat **fără** mesaj inițial: creează template-uri aprobate în Meta Business Manager:
     - `daily_briefing`, `weekly_review`, `agent_notification`
   - Configurează în `.env`:
     ```env
     WHATSAPP_TEMPLATE_DAILY=daily_briefing
     WHATSAPP_TEMPLATE_WEEKLY=weekly_review
     WHATSAPP_TEMPLATE_GENERAL=agent_notification
     WHATSAPP_TEMPLATE_LANGUAGE=ro
     ```

6. **Test rapid:**
   ```bash
   python -c "
   import src.bootstrap
   from src.integrations.notifier import get_notifier
   n = get_notifier()
   print('enabled:', n.enabled)
   print(n.send_message('Test Andrei AI Agents'))
   "
   ```

#### Opțiunea C — Discord Webhook (notificări one-way)

Folosește **Discord Incoming Webhook** — gratuit, pentru briefing-uri și alerte automate.

1. Discord → creează server privat (sau folosește unul existent)
2. **Server Settings** → **Integrations** → **Webhooks** → **New Webhook**
3. Alege canalul (ex: `#andreia-agents`) → **Copy Webhook URL**
4. `.env`:
   ```env
   NOTIFIER_PROVIDER=discord
   DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/...
   DISCORD_WEBHOOK_USERNAME=Andrei AI
   ```
5. **Test:**
   ```powershell
   .\scripts\local_run.ps1 discord
   ```

#### Opțiunea D — Discord Bot (chat bidirecțional)

Bot separat de webhook — răspunde la mesaje, citește/scrie Notion și Sheets.

1. [Discord Developer Portal](https://discord.com/developers/applications) → **New Application** → **Bot** → Token
2. **Privileged Gateway Intents** → **MESSAGE CONTENT INTENT** = ON
3. Invite bot pe server (Send Messages, Read Message History)
4. `.env`:
   ```env
   ENABLE_DISCORD_BOT=true
   DISCORD_BOT_TOKEN=...
   DISCORD_ALLOWED_CHANNEL_IDS=123456789012345678
   # DISCORD_ALLOWED_USER_IDS=...   # opțional
   ```
5. **Pornește:**
   ```powershell
   .\scripts\local_run.ps1 discord-bot
   ```

| | Telegram | Discord Webhook | Discord Bot | WhatsApp |
|---|----------|-----------------|-------------|----------|
| Setup | 5 min | 3 min | 15 min | 20–30 min |
| Cost | Gratuit | Gratuit | Gratuit | ~1000 conv/lună gratuit |
| Mesaje automate | Oricând | Oricând | La cerere | Template sau 24h |
| Chat interactiv | Da | Nu | **Da** | Limitat |
| Notion / Sheets | Nu | Nu | **Da** | Nu |

### Căutare web (doar la cerere explicită)

Nu se activează automat. Declanșează cu prefixe explicite în Discord:

```
caută: trenduri reels restaurante 2026
caută pe net caru cu bere cluj
search: content ideas beer garden
```

Flux: linkuri găsite → citește paginile → sugestii bazate pe conținut.

```env
ENABLE_WEB_SEARCH=true
WEB_SEARCH_MAX_RESULTS=5
WEB_SEARCH_FETCH_PAGES=true
WEB_SEARCH_MAX_PAGES_TO_READ=3
WEB_SEARCH_PAGE_CHAR_LIMIT=3500
WEB_SEARCH_FETCH_TIMEOUT_SECONDS=15
```

### Fallback LLMs (opțional dar recomandat)

```env
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
LLM_FALLBACK_ORDER=grok,anthropic,openai
```

---

## Docker (Local & Production)

```bash
# Build
docker compose build

# Scheduler + API + Dashboard
docker compose up -d

# Job-uri one-off
docker compose --profile jobs run daily
docker compose --profile jobs run weekly
docker compose --profile jobs run crew
```

---

## Deploy pe Hostinger VPS

Funcționează pe **Hostinger VPS (KVM)** cu Docker — nu pe shared hosting.

**Ghid complet:** [DEPLOY_HOSTINGER.md](DEPLOY_HOSTINGER.md)

```bash
# Pe VPS (după SSH ca root):
curl -fsSL https://raw.githubusercontent.com/YOUR_USER/andreia-agent-system/main/scripts/deploy_hostinger.sh -o deploy.sh
chmod +x deploy.sh
./deploy.sh --repo https://github.com/YOUR_USER/andreia-agent-system.git

# Sau din proiectul clonat:
chmod +x scripts/deploy_hostinger.sh
./scripts/deploy_hostinger.sh --with-dashboard
```

**Scripturi incluse:**
- `scripts/deploy_hostinger.sh` — instalare Docker, clone, build, deploy, Nginx opțional
- `scripts/setup_cron_hostinger.sh` — cron Linux (fără scheduler always-on)

**Cost estimat:** KVM 1 (~€5/lună) + Grok API (~$8) = **~€12/lună**

---

## Deploy pe Railway — Pas cu Pas

### Pas 1: Cont Railway

1. Mergi la [railway.app](https://railway.app)
2. Sign up cu GitHub
3. Confirmă email

### Pas 2: Push pe GitHub

```bash
git init
git add .
git commit -m "Initial commit: Andrei AI Agent System"
git remote add origin https://github.com/YOUR_USER/andreia-agent-system.git
git push -u origin main
```

### Pas 3: Conectare Repo

1. Railway Dashboard → **New Project**
2. **Deploy from GitHub repo**
3. Selectează `andreia-agent-system`
4. Railway detectează `Dockerfile` și `railway.json` automat

### Pas 4: Variabile de Mediu

În Railway → Service → **Variables**, adaugă TOATE variabilele din `.env.example`:

**Minim obligatorii pentru funcționare:**

```env
APP_ENV=production
XAI_API_KEY=xai-...
NOTION_API_KEY=secret_...
NOTION_TASKS_DB_ID=...
NOTIFIER_PROVIDER=telegram
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
# Sau WhatsApp:
# NOTIFIER_PROVIDER=whatsapp
# WHATSAPP_ACCESS_TOKEN=...
# WHATSAPP_PHONE_NUMBER_ID=...
# WHATSAPP_RECIPIENT=40722123456
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=...
SUPABASE_SERVICE_KEY=...
MEMORY_PROVIDER=supabase
TIMEZONE=Europe/Bucharest
ENABLE_SCHEDULER=true
```

**Recomandate:**

```env
ANTHROPIC_API_KEY=...
OPENAI_API_KEY=...
GOOGLE_CREDENTIALS_JSON={...}
GOOGLE_SHEET_AJUT_CUM_POT_ID=...
GOOGLE_SHEET_EDITOR_PIPELINE_ID=...
NOTION_IDEAS_DB_ID=...
ENABLE_DISCORD_BOT=true
DISCORD_BOT_TOKEN=...
DISCORD_ALLOWED_CHANNEL_IDS=...
ENABLE_WEB_SEARCH=true
NOTION_POSTING_PLAN_DB_ID=...
NOTION_AJUT_CUM_POT_DB_ID=...
NOTION_JOURNAL_DB_ID=...
NOTION_BRIEFINGS_PAGE_ID=...
```

> **Securitate:** Nu commita niciodată `.env`. Railway Variables sunt criptate. Nu loga chei în cod.

### Pas 5: Deploy

1. Click **Deploy** (sau push pe main → auto-deploy)
2. Așteaptă build-ul Docker (~2-5 min)
3. Verifică logs: Service → **Deployments** → View Logs
4. Health check: `https://your-app.railway.app/health`

### Pas 6: Cron Jobs (Scheduled Tasks)

Railway suportă cron jobs native. Creează **3 servicii cron** sau folosește un singur serviciu cu scheduler:

**Opțiunea A — Scheduler always-on (recomandat):**

Serviciul principal rulează `src/scheduler.py` care gestionează:
- Daily briefing: 07:00
- Weekly review: Duminică 20:00
- Smart alerts: 09:00, 14:00, 18:00

**Opțiunea B — Railway Cron (serverless):**

Creează servicii separate cu cron triggers:

| Serviciu | Cron Expression | Command |
|----------|----------------|---------|
| daily-briefing | `0 7 * * *` | `python run_daily.py` |
| weekly-review | `0 20 * * 0` | `python run_weekly.py` |
| smart-alerts | `0 9,14,18 * * *` | `python run_alerts.py` |

În Railway: Service → Settings → Cron Schedule.

### Pas 7: Monitorizare

**Logs:**
- Railway Dashboard → Service → Logs (real-time)
- Filtrează după `daily_briefing`, `crew_completed`, `error`

**Costuri:**
- Dashboard → Usage → setează budget alerts
- Vezi [COSTS.md](COSTS.md) pentru estimări

**Health:**
```bash
curl https://your-app.railway.app/health
# {"status":"ok","service":"andreia-agents"}
```

**Trigger manual (via API):**
```bash
curl -X POST https://your-app.railway.app/trigger/daily
curl -X POST https://your-app.railway.app/trigger/weekly
curl -X POST https://your-app.railway.app/trigger/alerts
```

### Pas 8: Dashboard (Opțional)

Creează un al doilea serviciu Railway:
- Start Command: `streamlit run src/dashboard/app.py --server.port=$PORT --server.address=0.0.0.0`
- Adaugă aceleași environment variables

---

## Discord Bot — Comenzi

Scrie în canalul configurat (`DISCORD_ALLOWED_CHANNEL_IDS`) sau menționează botul.

| Comandă / mesaj | Ce face |
|-----------------|---------|
| `help` / `ajutor` | Lista comenzilor |
| `daily` | Briefing zilnic (Notion + Calendar + Content Creation din Sheets) |
| `content` | Doar briefing Content Creation (lipsuri + gata de postat) |
| `weekly` | Review săptămânal |
| `idee: ...` | Plan de implementare + salvare automată în Notion Ideas (Draft) |
| `care sunt ideile in draft` | Listă idei Notion filtrate după status (citire directă, fără AI) |
| `da, salvează asta în Notion` | Salvează ultima conversație ca idee Draft |
| `caută pe net ...` / `caută: ...` | Căutare web + linkuri + sugestii din pagini citite |
| Chat liber | Task-uri Notion, Sheets, calendar, întrebări generale |

**Notă:** Botul ține memorie scurtă per canal (ultimele mesaje) pentru follow-up-uri (`salvează asta`). Ideile noi în Notion primesc automat **status = Draft**.

---

## Comenzi CLI

```bash
# Briefing zilnic (Telegram + Notion)
python run_daily.py

# Review săptămânal (Duminică)
python run_weekly.py

# Query custom la crew
python run_crew.py "analizeaza saptamana"
python run_crew.py "ce idei de content am?"
python run_crew.py "cum stau cu echilibrul familie-munca?"

# Cu mod specific
python run_crew.py --mode daily
python run_crew.py --mode weekly "recap saptamana"

# Fără notificări (doar output local)
python run_crew.py --no-notify "test rapid"

# Smart alerts
python run_alerts.py

# Scheduler (production)
python src/scheduler.py

# API server
python -m src.api.server

# Dashboard
streamlit run src/dashboard/app.py
```

---

## Securitate

### Reguli de Aur

1. **Niciodată** nu commita `.env`, credentials JSON, sau token-uri
2. Folosește **Railway Variables** sau **GitHub Secrets** pentru production
3. `.gitignore` exclude automat fișiere sensibile
4. Rotește cheile dacă sunt expuse accidental
5. Service Account Google: acordă doar permisiunile necesare
6. Notion: folosește integration token, nu user token
7. Supabase: folosește `service_role` key doar server-side

### Verificare pre-commit

```bash
# Verifică că nu ai secrete în repo
git secrets --scan  # sau
grep -r "xai-\|sk-ant-\|sk-\|secret_" --include="*.py" --include="*.env" .
```

---

## Troubleshooting

### "XAI_API_KEY not configured"
→ Verifică `.env` sau Railway Variables. Key-ul trebuie să înceapă cu `xai-`.

### Notion "object not found"
→ Database-ul nu e shared cu integrarea. Mergi la database → ... → Connections → Add integration.

### Notificările nu sosesc (Telegram/Discord/WhatsApp)

**Telegram:** Verifică `TELEGRAM_BOT_TOKEN` și `TELEGRAM_CHAT_ID`. Trimite `/start` botului înainte.

**Discord Webhook:** Verifică `DISCORD_WEBHOOK_URL` — trebuie să înceapă cu `https://discord.com/api/webhooks/`.

**Discord Bot:** Verifică `DISCORD_BOT_TOKEN`, `MESSAGE CONTENT INTENT` activ, canalul în `DISCORD_ALLOWED_CHANNEL_IDS`. Pornește cu `.\scripts\local_run.ps1 discord-bot`.

**Idei Notion inventate de AI:** Întrebările despre liste de idei (`care sunt ideile in draft`) folosesc citire directă din Notion. Pentru alte întrebări, agentul trebuie să apeleze tool-urile — nu inventa date.

**Căutare web:** Funcționează doar cu prefix explicit (`caută:`, `caută pe net`). Unele site-uri blochează citirea paginii (403) — botul folosește snippet-urile din căutare.

**WhatsApp:**
→ Verifică `WHATSAPP_ACCESS_TOKEN`, `WHATSAPP_PHONE_NUMBER_ID`, `WHATSAPP_RECIPIENT`
→ Token temporar expiră în 24h — generează **permanent token** pentru producție
→ Mesajele automate eșuează în afara ferestrei 24h — configurează template-uri sau scrie business number-ului o dată pe zi
→ Eroare `#131030` = număr recipient invalid (verifică format `407XXXXXXXX`)

### Google Calendar gol
→ Service account trebuie să aibă acces la calendar. Share calendar cu email-ul SA.

### CrewAI timeout / slow
→ Normal pentru primul run (inițializare). Reduce `max_iter` în `src/agents/definitions.py`.

### Railway build fail
→ Verifică logs. De obicei: dependențe lipsă sau Dockerfile path greșit.

### Memory not working
→ Rulează `scripts/supabase_schema.sql`. Verifică `SUPABASE_URL` și keys.

### LLM fallback chain
→ Dacă Grok e down, sistemul încearcă automat Claude → GPT-4o. Verifică logs pentru `llm_provider_failed`.

---

## Structură Proiect

```
andreia-agent-system/
├── src/
│   ├── agents/          # Definiții cei 5 agenți
│   ├── bot/             # Discord bot, context conversație, intent detection
│   ├── crew/            # CrewAI orchestration
│   ├── graph/           # LangGraph workflow
│   ├── integrations/    # Notion, Google, Discord, Sheets, web search, memory
│   ├── jobs/            # Daily, weekly, alerts
│   ├── tools/           # CrewAI tools
│   ├── llm/             # Grok + fallback providers
│   ├── api/             # HTTP server (Railway health)
│   ├── dashboard/       # Streamlit UI
│   └── utils/           # Config, logging
├── scripts/
│   ├── supabase_schema.sql
│   ├── setup_google_sheets.py
│   ├── local_run.ps1
│   ├── deploy_hostinger.sh
│   └── setup_cron_hostinger.sh
├── DEPLOY_HOSTINGER.md
├── run_crew.py          # CLI principal
├── run_discord_bot.py   # Discord bot interactiv
├── run_daily.py
├── run_weekly.py
├── run_alerts.py
├── src/scheduler.py     # Cron scheduler
├── Dockerfile
├── docker-compose.yml
├── railway.json
├── railway.toml
├── requirements.txt
├── .env.example
├── COSTS.md
└── README.md
```

---

## Costuri

Vezi [COSTS.md](COSTS.md) pentru estimări detaliate Light/Medium/Heavy.

**Start recomandat:** Railway Hobby ($5) + Grok API (~$8) + Supabase Free = **~$13/lună**.

---

## Licență

MIT — Proiect personal pentru Andrei.

---

*Construit cu empatie, pentru echilibrul viață-profesie.*