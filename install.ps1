# Colors (using Write-Host with -ForegroundColor)
Write-Host "#########################################" -ForegroundColor Cyan
Write-Host "#                                       #" -ForegroundColor Cyan
Write-Host "#         BOKU AIDC - Installer         #" -ForegroundColor Cyan
Write-Host "#                                       #" -ForegroundColor Cyan
Write-Host "#########################################" -ForegroundColor Cyan

Start-Sleep 1

# Check if installed
if (Test-Path "venv" -and Test-Path ".env") {
    Write-Host "Bot already installed. Updating dependencies..." -ForegroundColor Yellow
    & venv\Scripts\Activate.ps1
    pip install --upgrade pip
    pip install -r requirements.txt
    playwright install chromium
    Write-Host "Starting bot..." -ForegroundColor Green
    python zom_bot.py
    exit
}

# Step 1: Create virtual environment
Write-Host "Creating virtual environment..." -ForegroundColor Blue
python -m venv venv
& venv\Scripts\Activate.ps1

# Step 2: Install dependencies
Write-Host "Installing Python dependencies..." -ForegroundColor Blue
pip install --upgrade pip
pip install -r requirements.txt
playwright install chromium

# Step 3: Setup .env
Write-Host "Setting up Discord credentials..." -ForegroundColor Magenta
$DISCORD_TOKEN = Read-Host "Enter your Discord Bot Token"
$BOT_ID = Read-Host "Enter your Discord Bot ID"
@"
DISCORD_TOKEN=$DISCORD_TOKEN
BOT_ID=$BOT_ID
"@ | Out-File -Encoding utf8 .env
Write-Host ".env created!" -ForegroundColor Green

# Step 4: Launch Chromium for Gemini login
Write-Host "Opening Chromium for Gemini login..." -ForegroundColor Cyan
python - <<EOF
from playwright.sync_api import sync_playwright
import os
os.makedirs("playwright_data", exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context(storage_state="playwright_data/state.json")
    page = context.new_page()
    page.goto("https://gemini.google.com/")
    print("Please log in to Gemini. After login, type 'done' and press Enter.")
    input("Type 'done' once logged in: ")
    browser.close()
EOF

# Step 5: Start bot
Write-Host "Starting BOKU AIDC Bot..." -ForegroundColor Green
python zom_bot.py
