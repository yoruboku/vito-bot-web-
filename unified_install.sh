#!/usr/bin/env bash
set -euo pipefail

# Colors
GREEN="\033[1;32m"
YELLOW="\033[1;33m"
BLUE="\033[1;34m"
MAGENTA="\033[1;35m"
CYAN="\033[1;36m"
RED="\033[1;31m"
RESET="\033[0m"

BANNER() {
  echo -e "${CYAN}"
  echo "=========================================="
  echo "    V I T O   —   A I  D I S C O R D   B O T"
  echo "=========================================="
  echo -e "${RESET}"
}

confirm_yesno() {
  # $1 prompt
  while true; do
    read -rp "$1 [y/n]: " yn
    case "$yn" in
      [Yy]*) return 0;;
      [Nn]*) return 1;;
      *) echo "Please answer y or n.";;
    esac
  done
}

# Pick python binary
PYTHON_BIN=""
for p in python3 python py python; do
  if command -v "$p" >/dev/null 2>&1; then
    PYTHON_BIN="$p"
    break
  fi
done

BANNER

if [ -z "$PYTHON_BIN" ]; then
  echo -e "${RED}Python 3 not found on PATH. Install Python 3.9+ and re-run.${RESET}"
  exit 1
fi

echo -e "${GREEN}Using Python: $PYTHON_BIN${RESET}"

# If already installed (venv & .env), skip installation and run update+start
if [ -d "venv" ] && [ -f ".env" ]; then
  echo -e "${YELLOW}Existing installation detected. Updating dependencies and starting VITO...${RESET}"
  source venv/bin/activate
  pip install --upgrade pip
  pip install -r requirements.txt
  echo -e "${BLUE}Ensuring Playwright browsers installed...${RESET}"
  $PYTHON_BIN -m playwright install chromium
  echo -e "${GREEN}Starting VITO...${RESET}"
  $PYTHON_BIN main.py
  exit 0
fi

echo -e "${BLUE}Creating virtual environment...${RESET}"
$PYTHON_BIN -m venv venv
# shellcheck disable=SC1091
source venv/bin/activate

echo -e "${BLUE}Installing Python dependencies...${RESET}"
pip install --upgrade pip
pip install -r requirements.txt

echo -e "${BLUE}Installing Playwright Chromium...${RESET}"
$PYTHON_BIN -m playwright install chromium

# Ask for token & bot id with confirmation
while true; do
  read -rp "Enter your Discord Bot TOKEN: " DISCORD_TOKEN
  read -rp "Enter your Discord BOT ID (numeric): " BOT_ID
  echo
  echo -e "${MAGENTA}You entered:${RESET}"
  echo "DISCORD_TOKEN: ${DISCORD_TOKEN:0:6}... (hidden)"
  echo "BOT_ID: $BOT_ID"
  if confirm_yesno "Is this correct?"; then
    break
  else
    echo "Let's try again."
  fi
done

# Create .env
cat > .env <<EOF
DISCORD_TOKEN=$DISCORD_TOKEN
BOT_ID=$BOT_ID
EOF
chmod 600 .env
echo -e "${GREEN}.env created and secured.${RESET}"

# Create playwright_data directory
mkdir -p playwright_data
echo -e "${BLUE}Now we will open Chromium so you can login to Gemini.${RESET}"
echo -e "${YELLOW}When you finish logging in, return here and type 'done' to continue.${RESET}"
if confirm_yesno "Open Chromium now to login to Gemini?"; then
  # Launch a small Python helper to open the browser with the same user_data_dir
  $PYTHON_BIN - <<PYCODE
from playwright.sync_api import sync_playwright
import os, sys
os.makedirs("playwright_data", exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    page.goto("https://gemini.google.com/")
    print("Browser opened. Please log in to Gemini in the opened window.")
    try:
        inp = input("Type 'done' when you are logged in: ")
    except KeyboardInterrupt:
        inp = ""
    browser.close()
PYCODE
else
  echo "Okay — when you're ready, run: source venv/bin/activate && python - <<PYCODE ... (see README)"
fi

echo -e "${GREEN}Login step complete (session stored in the Playwright context).${RESET}"
echo -e "${BLUE}Starting VITO now...${RESET}"
$PYTHON_BIN main.py
