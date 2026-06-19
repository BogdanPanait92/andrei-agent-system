#!/usr/bin/env bash
# =============================================================================
# Andrei AI Agent System — Hostinger VPS Deploy Script
# Usage:
#   ./scripts/deploy_hostinger.sh
#   ./scripts/deploy_hostinger.sh --repo https://github.com/user/repo.git
#   ./scripts/deploy_hostinger.sh --update
#   ./scripts/deploy_hostinger.sh --cron-mode
#   ./scripts/deploy_hostinger.sh --nginx agents.example.com
# =============================================================================

set -euo pipefail

# --- Config ---
INSTALL_DIR="${INSTALL_DIR:-/opt/andreia-agent-system}"
REPO_URL=""
UPDATE_ONLY=false
CRON_MODE=false
NGINX_DOMAIN=""
SKIP_DOCKER_INSTALL=false
SERVICES="scheduler api discord-bot"

# --- Colors ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info()  { echo -e "${BLUE}[INFO]${NC} $*"; }
log_ok()    { echo -e "${GREEN}[OK]${NC} $*"; }
log_warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
log_error() { echo -e "${RED}[ERROR]${NC} $*"; }

usage() {
    cat <<EOF
Andrei AI Agent System — Hostinger VPS Deploy

Usage: $0 [OPTIONS]

Options:
  --repo URL          Git repository URL to clone
  --dir PATH          Install directory (default: /opt/andreia-agent-system)
  --update            Pull latest code and rebuild containers
  --cron-mode         Use Linux cron instead of scheduler container
  --nginx DOMAIN      Setup Nginx reverse proxy + suggest certbot
  --with-dashboard    Also start Streamlit dashboard container
  --skip-docker       Skip Docker installation check
  -h, --help          Show this help

Examples:
  $0 --repo https://github.com/user/andreia-agent-system.git
  $0 --update
  $0 --cron-mode --with-dashboard
  $0 --nginx agents.domeniultau.ro
EOF
}

# --- Parse args ---
WITH_DASHBOARD=false
while [[ $# -gt 0 ]]; do
    case "$1" in
        --repo)           REPO_URL="$2"; shift 2 ;;
        --dir)            INSTALL_DIR="$2"; shift 2 ;;
        --update)         UPDATE_ONLY=true; shift ;;
        --cron-mode)      CRON_MODE=true; SERVICES="api discord-bot"; shift ;;
        --nginx)          NGINX_DOMAIN="$2"; shift 2 ;;
        --with-dashboard) WITH_DASHBOARD=true; shift ;;
        --skip-docker)    SKIP_DOCKER_INSTALL=true; shift ;;
        -h|--help)        usage; exit 0 ;;
        *)                log_error "Unknown option: $1"; usage; exit 1 ;;
    esac
done

if $WITH_DASHBOARD; then
    SERVICES="$SERVICES dashboard"
fi

# --- Preflight ---
if [[ "$(id -u)" -ne 0 ]]; then
    log_error "Rulează ca root: sudo $0 $*"
    exit 1
fi

if ! $SKIP_DOCKER_INSTALL; then
    if ! command -v docker &>/dev/null; then
        log_info "Docker nu e instalat. Instalez..."
        apt-get update -qq
        apt-get install -y -qq curl ca-certificates
        curl -fsSL https://get.docker.com | sh
        systemctl enable docker
        systemctl start docker
        log_ok "Docker instalat."
    else
        log_ok "Docker deja instalat: $(docker --version)"
    fi

    if ! docker compose version &>/dev/null; then
        log_info "Instalez docker-compose-plugin..."
        apt-get update -qq
        apt-get install -y -qq docker-compose-plugin git
        log_ok "docker compose plugin instalat."
    fi
fi

# --- Clone or update repo ---
if $UPDATE_ONLY; then
    if [[ ! -d "$INSTALL_DIR" ]]; then
        log_error "Directorul $INSTALL_DIR nu există. Rulează fără --update mai întâi."
        exit 1
    fi
    log_info "Update din Git..."
    cd "$INSTALL_DIR"
    git pull --ff-only
    log_ok "Cod actualizat."
else
    if [[ -n "$REPO_URL" ]]; then
        if [[ -d "$INSTALL_DIR/.git" ]]; then
            log_warn "Repo există deja în $INSTALL_DIR. Fac pull..."
            cd "$INSTALL_DIR"
            git pull --ff-only || true
        else
            log_info "Clonez $REPO_URL → $INSTALL_DIR"
            mkdir -p "$(dirname "$INSTALL_DIR")"
            git clone "$REPO_URL" "$INSTALL_DIR"
            cd "$INSTALL_DIR"
        fi
    elif [[ -f "$(dirname "$0")/../docker-compose.yml" ]]; then
        INSTALL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
        cd "$INSTALL_DIR"
        log_info "Folosesc directorul curent: $INSTALL_DIR"
    else
        log_error "Specifică --repo URL sau rulează din directorul proiectului."
        exit 1
    fi
fi

# --- Timezone ---
log_info "Setez timezone Europe/Bucharest..."
timedatectl set-timezone Europe/Bucharest 2>/dev/null || \
    ln -sf /usr/share/zoneinfo/Europe/Bucharest /etc/localtime 2>/dev/null || true

# --- .env setup ---
if [[ ! -f "$INSTALL_DIR/.env" ]]; then
    if [[ -f "$INSTALL_DIR/.env.example" ]]; then
        cp "$INSTALL_DIR/.env.example" "$INSTALL_DIR/.env"
        chmod 600 "$INSTALL_DIR/.env"
        log_warn ".env creat din .env.example — EDITEAZĂ-L înainte de producție!"
        log_warn "  nano $INSTALL_DIR/.env"
    else
        log_error ".env lipsește și .env.example nu a fost găsit."
        exit 1
    fi
else
    chmod 600 "$INSTALL_DIR/.env"
    log_ok ".env există."
fi

# --- Logs dir ---
mkdir -p "$INSTALL_DIR/logs"
chmod 755 "$INSTALL_DIR/logs"

# --- Build & deploy ---
cd "$INSTALL_DIR"
log_info "Build imagini Docker..."
docker compose build --quiet 2>/dev/null || docker compose build

if $CRON_MODE; then
    log_info "Mod cron: opresc scheduler, pornesc doar API..."
    docker compose stop scheduler 2>/dev/null || true
    docker compose up -d $SERVICES
    if [[ -f "$INSTALL_DIR/scripts/setup_cron_hostinger.sh" ]]; then
        chmod +x "$INSTALL_DIR/scripts/setup_cron_hostinger.sh"
        "$INSTALL_DIR/scripts/setup_cron_hostinger.sh"
        log_ok "Cron jobs configurate."
    else
        log_warn "scripts/setup_cron_hostinger.sh lipsește — configurează cron manual."
    fi
else
    log_info "Pornesc servicii: $SERVICES"
    docker compose up -d $SERVICES
fi

# --- Wait for health ---
log_info "Aștept health check API..."
for i in $(seq 1 30); do
    if curl -sf http://localhost:8000/health &>/dev/null; then
        log_ok "API healthy!"
        break
    fi
    if [[ $i -eq 30 ]]; then
        log_warn "API nu răspunde încă. Verifică: docker compose logs api"
    fi
    sleep 2
done

# --- Firewall (optional, non-interactive safe) ---
if command -v ufw &>/dev/null && ufw status | grep -q "inactive"; then
    log_info "Configurez UFW (SSH + porturi aplicație)..."
    ufw allow OpenSSH &>/dev/null || ufw allow 22/tcp &>/dev/null || true
    ufw allow 8000/tcp &>/dev/null || true
    if $WITH_DASHBOARD; then
        ufw allow 8501/tcp &>/dev/null || true
    fi
    ufw --force enable &>/dev/null || true
    log_ok "UFW activat."
fi

# --- Nginx (optional) ---
if [[ -n "$NGINX_DOMAIN" ]]; then
    log_info "Configurez Nginx pentru $NGINX_DOMAIN..."
    apt-get install -y -qq nginx certbot python3-certbot-nginx 2>/dev/null || true

    cat > "/etc/nginx/sites-available/andreia" <<NGINX
server {
    listen 80;
    server_name ${NGINX_DOMAIN};

    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_read_timeout 86400;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000/;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
    }

    location /health {
        proxy_pass http://127.0.0.1:8000/health;
    }
}
NGINX

    ln -sf /etc/nginx/sites-available/andreia /etc/nginx/sites-enabled/andreia
    rm -f /etc/nginx/sites-enabled/default 2>/dev/null || true
    nginx -t && systemctl reload nginx
    log_ok "Nginx configurat. Rulează pentru HTTPS:"
    echo "  certbot --nginx -d ${NGINX_DOMAIN}"
fi

# --- Summary ---
echo ""
echo "=============================================="
echo -e "${GREEN}  Deploy complet!${NC}"
echo "=============================================="
echo "  Director:  $INSTALL_DIR"
echo "  API:       http://localhost:8000/health"
if $WITH_DASHBOARD || [[ "$SERVICES" == *"dashboard"* ]]; then
    echo "  Dashboard: http://localhost:8501"
fi
if [[ -n "$NGINX_DOMAIN" ]]; then
    echo "  Public:    http://${NGINX_DOMAIN}"
fi
echo ""
echo "  Comenzi utile:"
echo "    cd $INSTALL_DIR"
echo "    docker compose ps"
    echo "    docker compose logs -f scheduler"
    echo "    docker compose logs -f discord-bot"
echo "    docker compose --profile jobs run --rm daily"
echo ""
if grep -q "your_xai_api_key" "$INSTALL_DIR/.env" 2>/dev/null; then
    echo -e "${YELLOW}  ⚠ Editează .env cu cheile reale:${NC}"
    echo "    nano $INSTALL_DIR/.env"
    echo "    docker compose up -d --build"
fi
echo "=============================================="