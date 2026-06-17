# Deploy pe Hostinger VPS — Andrei AI Agent System

Ghid complet pentru rularea sistemului agentic pe **Hostinger VPS** cu Docker.

> **Important:** Funcționează doar pe **VPS** (KVM), nu pe shared/web hosting.

---

## Cerințe

| Resursă | Minim | Recomandat |
|---------|-------|------------|
| Plan | Hostinger KVM 1 | Hostinger KVM 2 |
| RAM | 4 GB | 8 GB |
| OS | Ubuntu 22.04/24.04 | Ubuntu 24.04 |
| Docker | Da | Da (+ Docker Manager) |

**API keys necesare înainte de deploy:** Grok (xAI), Notion, Telegram **sau** WhatsApp, Supabase. Vezi `.env.example`.

---

## Arhitectură pe VPS

```
┌──────────────── Hostinger VPS ────────────────┐
│  docker compose                                │
│  ┌─────────────┐ ┌─────┐ ┌──────────────────┐ │
│  │  scheduler  │ │ API │ │ Streamlit :8501  │ │
│  │  (cron int) │ │:8000│ │   (dashboard)    │ │
│  └─────────────┘ └─────┘ └──────────────────┘ │
│         │                                      │
│  Opțional: Nginx reverse proxy + HTTPS        │
└────────────────────────────────────────────────┘
         │
    Notion · Google · Telegram · Supabase · Grok API
```

---

## Metoda 1: Deploy automat (recomandat)

### Pas 1 — Cumpără și configurează VPS

1. [hostinger.com/vps](https://www.hostinger.com/vps-hosting) → alege **KVM 1** sau **KVM 2**
2. OS: **Ubuntu 24.04**
3. hPanel → VPS → **SSH Access** → notează IP, user (`root`), parolă
4. (Opțional) Adaugă cheie SSH publică pentru login fără parolă

### Pas 2 — Conectare SSH

```bash
ssh root@IP_VPS_TAU
```

### Pas 3 — Rulează scriptul de deploy

**Varianta A — din GitHub (după ce ai push-at proiectul):**

```bash
curl -fsSL https://raw.githubusercontent.com/YOUR_USER/andreia-agent-system/main/scripts/deploy_hostinger.sh -o deploy.sh
chmod +x deploy.sh
./deploy.sh --repo https://github.com/YOUR_USER/andreia-agent-system.git
```

**Varianta B — upload manual + script local:**

```bash
# Pe VPS, după git clone:
cd andreia-agent-system
chmod +x scripts/deploy_hostinger.sh
./scripts/deploy_hostinger.sh
```

### Pas 4 — Configurează `.env`

Scriptul creează `.env` din `.env.example` dacă lipsește. Editează-l:

```bash
nano /opt/andreia-agent-system/.env
```

**Minim obligatoriu:**

```env
APP_ENV=production
XAI_API_KEY=xai-...
NOTION_API_KEY=secret_...
NOTION_TASKS_DB_ID=...
NOTIFIER_PROVIDER=telegram
TELEGRAM_BOT_TOKEN=...
TELEGRAM_CHAT_ID=...
# Sau WhatsApp: NOTIFIER_PROVIDER=whatsapp + WHATSAPP_* vars
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_KEY=...
SUPABASE_SERVICE_KEY=...
MEMORY_PROVIDER=supabase
TIMEZONE=Europe/Bucharest
ENABLE_SCHEDULER=true
```

Apoi repornește:

```bash
cd /opt/andreia-agent-system
docker compose up -d --build
```

### Pas 5 — Verificare

```bash
curl http://localhost:8000/health
# {"status":"ok","service":"andreia-agents"}

docker compose ps
docker compose logs -f scheduler
```

---

## Metoda 2: Deploy manual pas cu pas

### 1. Instalare Docker

```bash
apt update && apt upgrade -y
curl -fsSL https://get.docker.com | sh
systemctl enable docker
apt install -y docker-compose-plugin git
```

### 2. Clonează proiectul

```bash
mkdir -p /opt/andreia-agent-system
cd /opt
git clone https://github.com/YOUR_USER/andreia-agent-system.git
cd andreia-agent-system
```

### 3. Environment

```bash
cp .env.example .env
nano .env
```

### 4. Supabase schema

Rulează `scripts/supabase_schema.sql` în Supabase SQL Editor (o singură dată).

### 5. Build & start

```bash
docker compose build
docker compose up -d
```

### 6. Firewall

```bash
ufw allow OpenSSH
ufw allow 8000/tcp   # API (opțional, extern)
ufw allow 8501/tcp   # Dashboard (opțional, extern)
ufw enable
```

---

## Opțiuni de rulare

### Opțiunea A — Scheduler always-on (implicit)

`docker-compose.yml` pornește containerul `scheduler` care rulează:
- Daily briefing: **07:00** (Europe/Bucharest)
- Weekly review: **Duminică 20:00**
- Smart alerts: **09:00, 14:00, 18:00**

```bash
docker compose up -d scheduler api
# + dashboard dacă vrei UI:
docker compose up -d dashboard
```

### Opțiunea B — Cron Linux (economisește RAM)

Oprești scheduler-ul și lași doar API-ul (sau nimic always-on):

```bash
docker compose stop scheduler
chmod +x scripts/setup_cron_hostinger.sh
./scripts/setup_cron_hostinger.sh
```

Cron-ul va rula job-urile prin `docker compose run --rm`.

### Opțiunea C — Docker Manager (UI Hostinger)

1. hPanel → VPS → **Docker Manager**
2. **Deploy Container** → importă `docker-compose.yml`
3. Setează environment variables din `.env` în UI
4. Deploy

---

## Nginx + HTTPS (producție)

Pentru acces securizat la dashboard/API de pe internet:

```bash
apt install -y nginx certbot python3-certbot-nginx
```

Creează `/etc/nginx/sites-available/andreia`:

```nginx
server {
    listen 80;
    server_name agents.domeniultau.ro;

    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_set_header Host $host;
    }
}
```

```bash
ln -s /etc/nginx/sites-available/andreia /etc/nginx/sites-enabled/
nginx -t && systemctl reload nginx
certbot --nginx -d agents.domeniultau.ro
```

---

## Comenzi utile pe VPS

```bash
cd /opt/andreia-agent-system

# Status
docker compose ps

# Logs live
docker compose logs -f scheduler
docker compose logs -f api

# Repornire după update .env
docker compose down && docker compose up -d --build

# Job manual
docker compose --profile jobs run --rm daily
docker compose --profile jobs run --rm weekly
docker compose --profile jobs run --rm alerts
docker compose --profile jobs run --rm crew python run_crew.py "analizeaza saptamana"

# Update cod din GitHub
git pull
docker compose up -d --build

# Health check
curl http://localhost:8000/health
curl -X POST http://localhost:8000/trigger/daily
```

---

## Monitorizare

### Logs

```bash
# Ultimele 100 linii scheduler
docker compose logs --tail=100 scheduler

# Log persistent (dacă e configurat)
tail -f /opt/andreia-agent-system/logs/*.log
```

### Resurse VPS

```bash
docker stats
htop
df -h
```

### hPanel

- VPS → **Resource Usage** — CPU, RAM, disk
- Setează alerte email la 80% utilizare

---

## Troubleshooting

### Container nu pornește

```bash
docker compose logs api
docker compose logs scheduler
```

Verifică `.env` — cel mai des lipsește `XAI_API_KEY` sau `NOTION_API_KEY`.

### Notificările nu sosesc (Telegram/WhatsApp)

```bash
docker compose exec api python -c "
import src.bootstrap
from src.integrations.notifier import get_notifier
n = get_notifier()
print('provider:', n.__class__.__name__)
print('enabled:', n.enabled)
print(n.send_message('Test de pe Hostinger VPS'))
"
```

**WhatsApp:** token temporar expiră — folosește permanent token. Pentru cron jobs, configurează template-uri Meta.

### Out of memory (KVM 1)

```bash
# Oprește dashboard-ul dacă nu îl folosești
docker compose stop dashboard

# Sau treci pe cron mode (fără scheduler always-on)
docker compose stop scheduler
./scripts/setup_cron_hostinger.sh
```

### Port deja folosit

```bash
ss -tlnp | grep -E '8000|8501'
# Schimbă porturile în docker-compose.yml sau oprește serviciul conflictual
```

### Docker nu e instalat

```bash
curl -fsSL https://get.docker.com | sh
```

### Job-urile nu rulează la ora corectă

Verifică timezone:

```bash
timedatectl set-timezone Europe/Bucharest
docker compose exec scheduler date
```

---

## Securitate pe VPS

1. **Schimbă parola root** sau folosește doar chei SSH
2. **Dezactivează login parolă SSH** după ce ai cheie:
   ```bash
   # /etc/ssh/sshd_config → PasswordAuthentication no
   ```
3. **Nu expune porturile 8000/8501** public fără Nginx + HTTPS
4. **`.env` are permisiuni restrictive:**
   ```bash
   chmod 600 /opt/andreia-agent-system/.env
   ```
5. **Actualizări regulate:**
   ```bash
   apt update && apt upgrade -y
   docker compose pull && docker compose up -d --build
   ```

---

## Costuri Hostinger

| Componentă | Cost/lună |
|------------|-----------|
| KVM 1 VPS | ~€4–5 |
| KVM 2 VPS | ~€6–8 |
| Grok API (Light) | ~$8 |
| Supabase Free | $0 |
| **Total start** | **~€12–15/lună** |

Vezi [COSTS.md](COSTS.md) pentru detalii complete Light/Medium/Heavy.

---

## Railway vs Hostinger — când alegi ce

| Alege **Hostinger VPS** | Alege **Railway** |
|-------------------------|-------------------|
| Cost fix, predictibil | Deploy din GitHub cu 1 click |
| Control complet (root) | Zero administrare server |
| Ai deja cont Hostinger | Vrei cron native în UI |
| OK cu SSH ocazional | Vrei scalare automată |

---

## Quick Reference

```bash
# Deploy complet (prima dată)
./scripts/deploy_hostinger.sh --repo https://github.com/YOUR_USER/andreia-agent-system.git

# Doar update
./scripts/deploy_hostinger.sh --update

# Cron mode (fără scheduler container)
./scripts/deploy_hostinger.sh --cron-mode

# Cu Nginx
./scripts/deploy_hostinger.sh --nginx agents.domeniultau.ro
```

---

*Ultima actualizare: iunie 2026*