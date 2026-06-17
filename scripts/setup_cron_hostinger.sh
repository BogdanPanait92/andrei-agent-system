#!/usr/bin/env bash
# =============================================================================
# Configurează cron jobs Linux pentru Andrei AI Agent System pe Hostinger VPS
# Rulează job-urile prin Docker fără container scheduler always-on.
# =============================================================================

set -euo pipefail

INSTALL_DIR="${INSTALL_DIR:-/opt/andreia-agent-system}"
LOG_DIR="${INSTALL_DIR}/logs"

if [[ -d "$(dirname "$0")/.." ]] && [[ -f "$(dirname "$0")/../docker-compose.yml" ]]; then
    INSTALL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
fi

mkdir -p "$LOG_DIR"

CRON_FILE="/etc/cron.d/andreia-agents"

cat > "$CRON_FILE" <<CRON
# Andrei AI Agent System — scheduled jobs
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

# Daily briefing — 07:00 Europe/Bucharest
0 7 * * * root cd ${INSTALL_DIR} && docker compose --profile jobs run --rm daily >> ${LOG_DIR}/daily.log 2>&1

# Weekly review — Duminică 20:00
0 20 * * 0 root cd ${INSTALL_DIR} && docker compose --profile jobs run --rm weekly >> ${LOG_DIR}/weekly.log 2>&1

# Smart alerts — 09:00, 14:00, 18:00
0 9,14,18 * * * root cd ${INSTALL_DIR} && docker compose --profile jobs run --rm alerts >> ${LOG_DIR}/alerts.log 2>&1
CRON

chmod 644 "$CRON_FILE"

# Ensure cron service is running
if command -v systemctl &>/dev/null; then
    systemctl enable cron 2>/dev/null || systemctl enable crond 2>/dev/null || true
    systemctl start cron 2>/dev/null || systemctl start crond 2>/dev/null || true
fi

echo "[OK] Cron jobs instalate în $CRON_FILE"
echo ""
echo "Program:"
echo "  Daily briefing:  07:00 zilnic"
echo "  Weekly review:   Duminică 20:00"
echo "  Smart alerts:    09:00, 14:00, 18:00"
echo ""
echo "Logs:"
echo "  ${LOG_DIR}/daily.log"
echo "  ${LOG_DIR}/weekly.log"
echo "  ${LOG_DIR}/alerts.log"
echo ""
echo "Verificare:"
echo "  cat $CRON_FILE"
echo "  docker compose --profile jobs run --rm daily"