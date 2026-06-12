#!/usr/bin/env bash
set -euo pipefail

# Prometheus Auto-Updater
# Usage: ./update.sh          (interactive)
#        ./update.sh --auto   (non-interactive, for cron)

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INSTALL_DIR="/opt/prometheus"
LOG_FILE="/var/log/prometheus-update.log"
AUTO_MODE=0

if [[ "${1:-}" == "--auto" ]]; then
  AUTO_MODE=1
fi

log() {
  echo "[prometheus-update] $(date '+%Y-%m-%d %H:%M:%S') $*"
  echo "[prometheus-update] $(date '+%Y-%m-%d %H:%M:%S') $*" >> "$LOG_FILE" 2>/dev/null || true
}

need_sudo() { if [[ $EUID -ne 0 ]]; then echo "sudo"; fi; }
SUDO="$(need_sudo)"

# Determine which directory has the git repo
if [[ -d "$INSTALL_DIR/.git" ]]; then
  REPO_DIR="$INSTALL_DIR"
elif [[ -d "$PROJECT_DIR/.git" ]]; then
  REPO_DIR="$PROJECT_DIR"
else
  log "❌ Cannot find git repo in $INSTALL_DIR or $PROJECT_DIR"
  exit 1
fi

log "Checking for updates in $REPO_DIR ..."
cd "$REPO_DIR"

# Fetch latest
git fetch origin main 2>&1 | while read -r line; do log "  $line"; done

# Check if there are updates
LOCAL=$(git rev-parse HEAD)
REMOTE=$(git rev-parse origin/main)

if [[ "$LOCAL" == "$REMOTE" ]]; then
  log "✅ Already up to date. ($LOCAL)"
  exit 0
fi

log "Update available: $LOCAL -> $REMOTE"

if [[ "$AUTO_MODE" -eq 0 ]]; then
  echo ""
  echo "Changes:"
  git log --oneline HEAD..origin/main
  echo ""
  read -rp "Apply update? [Y/n] " confirm
  if [[ "${confirm,,}" == "n" ]]; then
    log "Update cancelled by user."
    exit 0
  fi
fi

# Pull updates
log "Pulling latest code..."
git pull origin main 2>&1 | while read -r line; do log "  $line"; done

# Sync to install dir if repo is separate
if [[ "$REPO_DIR" != "$INSTALL_DIR" ]]; then
  log "Syncing to $INSTALL_DIR ..."
  $SUDO rsync -a --delete \
    --exclude '.git' \
    --exclude 'data/' \
    --exclude 'models/' \
    "$REPO_DIR/" "$INSTALL_DIR/"
fi

# Rebuild and restart containers
log "Rebuilding containers..."
cd "$INSTALL_DIR"

if groups | grep -q docker; then
  docker compose up -d --build 2>&1 | while read -r line; do log "  $line"; done
else
  sg docker -c "docker compose up -d --build" 2>&1 | while read -r line; do log "  $line"; done
fi

log "✅ Update complete! New version: $(git rev-parse --short HEAD)"
log "Services status:"
if groups | grep -q docker; then
  docker compose ps
else
  sg docker -c "docker compose ps"
fi
