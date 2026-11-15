#!/bin/bash
# AndreaServer - bootstrap: scarica il repository e avvia l'installatore.
#   bash <(curl -fsSL https://raw.githubusercontent.com/andreafis/andreaserver/main/bootstrap.sh)
set -euo pipefail
REPO="${ANDREASERVER_REPO:-https://github.com/andreafis/andreaserver.git}"
DEST=/opt/andreaserver
[ "$(id -u)" = 0 ] || { echo "Run as root / Esegui come root"; exit 1; }
command -v git >/dev/null || { apt-get update && apt-get install -y git; }
if [ -d "$DEST/.git" ]; then git -C "$DEST" pull --ff-only; else git clone --depth 1 "$REPO" "$DEST"; fi
exec "$DEST/install.sh" "$@" </dev/tty
