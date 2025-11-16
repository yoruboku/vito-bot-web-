#!/usr/bin/env bash
set -euo pipefail

CYAN="\033[1;36m"; MAGENTA="\033[1;35m"; GREEN="\033[1;32m"; YELLOW="\033[1;33m"; RED="\033[1;31m"; RESET="\033[0m"

banner() {
  clear
  echo -e "${MAGENTA}"
  echo "██╗   ██╗██╗████████╗ ██████╗ "
  echo "██║   ██║██║╚══██╔══╝██╔═══██╗"
  echo "██║   ██║██║   ██║   ██║   ██║"
  echo "██║   ██║██║   ██║   ██║   ██║"
  echo "╚██████╔╝██║   ██║   ╚██████╔╝"
  echo " ╚═════╝ ╚═╝   ╚═╝    ╚═════╝ "
  echo -e "${CYAN}         V I T O   I N S T A L L E R${RESET}\n"
}

detect_python() {
  for p in python3 python py; do
    if command -v "$p" >/dev/null 2>&1; then
      PY="$p"
      return
    fi
  done
  echo -e "${RED}Python 3 not found.${RESET}"
  exit 1
}

chmod_helpers() {
  echo -e "${CYAN}[*] Setting execute bit on helper scripts (if present)...${RESET}"
  for f in install.sh update.sh open_gemini.sh; do
    if [ -f "$f" ]; then
      chmod +x "$f"
      echo -e "   ${GREEN}[✓]${RESET} $f"
    fi
  done
}

install_or_reinstall() {
  banner
  detect_python

  echo -e "${CYAN}[*] Creating virtual env and installing dependencies...${RESET}"
  $PY -m venv venv
  # shellcheck disable=SC1091
  source venv/bin/activate
  pip install --upgrade pip
  pip install -r requirements.txt
  $PY -m playwright install chromium

  # Token + ID with confirm loop
  while true; do
    echo
    echo -e "${CYAN}Discord credentials:${RESET}"
    read -rp "Bot Token: " TOKEN
    read -rp "Application/Bot ID: " BID

    echo -e "${YELLOW}\nYou entered:${RESET}"
    echo "  TOKEN: ${TOKEN:0:8}..."
    echo "  ID   : $BID"
    read -rp "Is this correct? (y/n): " ok
    case "$ok" in
      [Yy]*) break ;;
      *) echo -e "${RED}Re-entering credentials...${RESET}" ;;
    esac
  done

  echo -e "${CYAN}\nOpening Chromium. Log into Gemini, then CLOSE the browser to continue.${RESET}\n"

  $PY << 'EOF'
from playwright.sync_api import sync_playwright
import os
os.makedirs("playwright_data", exist_ok=True)
with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context("playwright_data", headless=False)
    page = ctx.new_page()
    page.goto("https://gemini.google.com")
    print("Log in to Gemini in the opened browser.")
    print("When login is complete, close the browser window.")
    ctx.wait_for_event("close", timeout=900000)
EOF

  echo -e "${GREEN}Gemini login saved.${RESET}\n"

  # Owner selection
  echo -e "${CYAN}Owner configuration:${RESET}"
  echo "  1) Default (only 'yoruboku' has special priority)"
  echo "  2) Set one extra owner username"
  read -rp "Select [1-2] (Enter = 1): " ow_choice
  ow_choice=${ow_choice:-1}
  OWNER_USERNAME=""

  if [ "$ow_choice" = "2" ]; then
    read -rp "Owner's Discord username (global username, case-insensitive): " OWNER_USERNAME
  fi

  # write .env
  cat > .env <<EOF
DISCORD_TOKEN=$TOKEN
BOT_ID=$BID
OWNER_USERNAME=$OWNER_USERNAME
EOF

  chmod 600 .env
  chmod_helpers

  echo -e "${GREEN}\nInstallation complete. Starting VITO...${RESET}\n"
  $PY main.py
}

start_vito() {
  detect_python
  if [ ! -d venv ] || [ ! -f .env ]; then
    echo -e "${RED}No installation detected. Run Install/Reinstall first.${RESET}"
    exit 1
  fi
  # shellcheck disable=SC1091
  source venv/bin/activate
  $PY main.py
}

# ---------- main ----------
banner
echo -e "${YELLOW}1) Install / Reinstall\n2) Start VITO\n${RESET}"
read -rp "Select: " choice

case "$choice" in
  1) install_or_reinstall ;;
  2) start_vito ;;
  *) echo -e "${RED}Invalid choice.${RESET}" ;;
esac
