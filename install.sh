#!/usr/bin/env bash
set -euo pipefail

# install.sh — Robust installer for VITO (Linux / macOS)
# Usage: chmod +x install.sh && ./install.sh

# -------------------------
# Colors & helpers
# -------------------------
GREEN="\033[1;32m"
YELLOW="\033[1;33m"
BLUE="\033[1;34m"
MAGENTA="\033[1;35m"
CYAN="\033[1;36m"
RED="\033[1;31m"
RESET="\033[0m"

BANNER() {
  echo -e "${CYAN}"
  echo "==============================================="
  echo "      V I T O   —   A I  D I S C O R D   B O T"
  echo "==============================================="
  echo -e "${RESET}"
}

info()  { echo -e "${BLUE}[INFO]${RESET}  $*"; }
ok()    { echo -e "${GREEN}[OK]${RESET}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${RESET}  $*"; }
err()   { echo -e "${RED}[ERR]${RESET}   $*"; }

confirm_yesno() {
  # prompt, returns 0 for yes, 1 for no
  local prompt="${1:-Are you sure?}"
  while true; do
    read -rp "${prompt} [y/n]: " yn
    case "${yn,,}" in
      y|yes) return 0;;
      n|no)  return 1;;
      *) echo "Please answer y or n.";;
    esac
  done
}

valid_number() {
  [[ "$1" =~ ^[0-9]+$ ]]
}

# -------------------------
# Choose Python binary
# -------------------------
BANNER
PYTHON_BIN=""
for p in python3 python py python; do
  if command -v "$p" >/dev/null 2>&1; then
    # require >=3.9
    ver=$($p -c 'import sys; print(".".join(map(str,sys.version_info[:2])))' 2>/dev/null || echo "0")
    major=${ver%%.*}
    minor=${ver#*.}
    if [[ "$major" -ge 3 ]] && [[ "${minor:-0}" -ge 9 || "$major" -gt 3 ]]; then
      PYTHON_BIN="$p"
      break
    fi
  fi
done

if [ -z "$PYTHON_BIN" ]; then
  err "Python 3.9+ not found on PATH. Install Python 3.9 or newer and re-run."
  exit 1
fi

ok "Using Python: $PYTHON_BIN ($( $PYTHON_BIN -V 2>&1 ))"

# -------------------------
# Already installed? update+start
# -------------------------
if [ -d "venv" ] && [ -f ".env" ]; then
  warn "Existing installation detected."
  if confirm_yesno "Do you want to update dependencies and start VITO now?"; then
    info "Activating venv..."
    # shellcheck disable=SC1091
    source venv/bin/activate
    info "Upgrading pip and reinstalling requirements..."
    pip install --upgrade pip
    pip install -r requirements.txt
    info "Ensuring Playwright browsers installed..."
    $PYTHON_BIN -m playwright install chromium
    ok "Dependencies updated. Starting VITO..."
    exec $PYTHON_BIN main.py
  else
    info "Exiting without changes."
    exit 0
  fi
fi

# -------------------------
# Create venv
# -------------------------
info "Creating Python virtual environment (venv)..."
$PYTHON_BIN -m venv venv
# shellcheck disable=SC1091
source venv/bin/activate

info "Upgrading pip and installing requirements..."
pip install --upgrade pip
if [ -f requirements.txt ]; then
  pip install -r requirements.txt
else
  warn "requirements.txt not found — proceeding without pip installs."
fi

# Playwright install
info "Installing Playwright and Chromium..."
$PYTHON_BIN -m pip install --upgrade pip
$PYTHON_BIN -m pip install playwright >/dev/null 2>&1 || true
$PYTHON_BIN -m playwright install chromium

# -------------------------
# Ask for DISCORD token & BOT ID (with confirm)
# -------------------------
info "Now we will configure your Discord credentials (this will create a local .env file)."
while true; do
  read -rp "Enter your Discord Bot TOKEN: " DISCORD_TOKEN
  read -rp "Enter your Discord BOT ID (numeric): " BOT_ID

  echo
  echo -e "${MAGENTA}You entered:${RESET}"
  if [ "${#DISCORD_TOKEN}" -ge 8 ]; then
    echo "DISCORD_TOKEN: ${DISCORD_TOKEN:0:6}... (hidden)"
  else
    echo "DISCORD_TOKEN: (looks short — double-check!)"
  fi
  echo "BOT_ID: $BOT_ID"

  if ! valid_number "$BOT_ID"; then
    warn "BOT_ID must be numeric. Try again."
    continue
  fi

  if confirm_yesno "Is this correct?"; then
    break
  fi
  echo "Let's try again."
done

# Create .env
cat > .env <<EOF
DISCORD_TOKEN=$DISCORD_TOKEN
BOT_ID=$BOT_ID
EOF
chmod 600 .env
ok ".env created and secured."

# -------------------------
# Prepare Playwright data dir and open Chromium for login
# -------------------------
mkdir -p playwright_data
info "Next step: open Chromium so you can manually log in to Gemini."
echo -e "${YELLOW}When the browser opens, log into your Google account and open https://gemini.google.com/ . After successful login, return to this terminal and type 'done'.${RESET}"

if confirm_yesno "Open Chromium now to login to Gemini?"; then
  # Launch persistent Playwright context so cookies/session are saved
  $PYTHON_BIN - <<'PYCODE'
from playwright.sync_api import sync_playwright
import os, sys, time
os.makedirs("playwright_data", exist_ok=True)
with sync_playwright() as p:
    print("Launching Chromium (headful). Please log in to Gemini in the opened browser window.")
    context = p.chromium.launch_persistent_context(user_data_dir="playwright_data", headless=False)
    page = context.new_page()
    page.goto("https://gemini.google.com/")
    print("When you're logged in, return here and type 'done' in the terminal to continue.")
    try:
        while True:
            v = input().strip().lower()
            if v == "done":
                break
    except KeyboardInterrupt:
        print("\nInterrupted; closing browser and exiting.")
    # save storage state explicitly
    context.storage_state(path="playwright_data/state.json")
    print("Login state saved to playwright_data/state.json")
    context.close()
PYCODE
else
  warn "You chose not to open Chromium now. You can log in later by running:"
  echo "  source venv/bin/activate && $PYTHON_BIN - <<PYCODE"
  echo "    from playwright.sync_api import sync_playwright"
  echo "    with sync_playwright() as p:"
  echo "      context = p.chromium.launch_persistent_context(user_data_dir='playwright_data', headless=False)"
  echo "      page = context.new_page(); page.goto('https://gemini.google.com/')"
  echo "      input('Type done after login: ')"
  echo "      context.storage_state(path='playwright_data/state.json')"
  echo "      context.close()"
  echo "  PYCODE"
  if ! confirm_yesno "Continue installation without logging into Gemini now? (you'll have to login later)"; then
    info "Exiting. Run the installer again when ready."
    exit 0
  fi
fi

# -------------------------
# Final: start the bot
# -------------------------
ok "Login step complete (if you logged in). Starting VITO now..."
exec $PYTHON_BIN main.py
