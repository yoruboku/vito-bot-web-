Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Show-Banner {
    Write-Host "██╗   ██╗██╗████████╗ ██████╗ " -ForegroundColor Magenta
    Write-Host "██║   ██║██║╚══██╔══╝██╔═══██╗" -ForegroundColor Magenta
    Write-Host "██║   ██║██║   ██║   ██║   ██║" -ForegroundColor Magenta
    Write-Host "██║   ██║██║   ██║   ██║   ██║" -ForegroundColor Magenta
    Write-Host "╚██████╔╝██║   ██║   ╚██████╔╝" -ForegroundColor Magenta
    Write-Host " ╚═════╝ ╚═╝   ╚═╝    ╚═════╝ " -ForegroundColor Magenta
    Write-Host "        VITO · AI CORE INSTALLER" -ForegroundColor Cyan
    Write-Host ""
}

Show-Banner

# Python detection
$pyCmd = (Get-Command python, python3, py -ErrorAction SilentlyContinue | Select-Object -First 1)
if (-not $pyCmd) {
    Write-Host "[!] Python 3.11+ not found. Install Python first." -ForegroundColor Red
    exit 1
}
$PY = $pyCmd.Source
Write-Host "[✓] Using Python: $PY" -ForegroundColor Green

function Run-Bot {
    Write-Host "[*] Starting VITO..." -ForegroundColor Cyan
    & venv\Scripts\Activate.ps1
    & $PY main.py
}

function Do-Install {
    Clear-Host
    Show-Banner

    Write-Host "▶ STEP 1: Virtual environment" -ForegroundColor Blue
    & $PY -m venv venv
    & venv\Scripts\Activate.ps1

    Write-Host "▶ STEP 2: Dependencies" -ForegroundColor Blue
    pip install --upgrade pip
    pip install -r requirements.txt
    & $PY -m playwright install chromium

    # Credentials
    Write-Host "▶ STEP 3: Discord credentials" -ForegroundColor Blue
    while ($true) {
        $token = Read-Host "Discord BOT TOKEN"
        $botId = Read-Host "Discord BOT ID (numeric)"

        if ($botId -notmatch '^\d+$') {
            Write-Host "[!] BOT ID must be numeric." -ForegroundColor Red
            continue
        }

        Write-Host ("TOKEN: {0}..." -f ($token.Substring(0, [Math]::Min(8, $token.Length)))) -ForegroundColor Magenta
        Write-Host ("BOT ID: {0}" -f $botId) -ForegroundColor Magenta
        $ok = Read-Host "Is this correct? (y/n)"
        if ($ok -match '^[Yy]') { break }
    }

    # Owner configuration
    Write-Host "▶ STEP 4: Owner configuration" -ForegroundColor Blue
    Write-Host "  1) Default (priority 'yoruboku' only)" -ForegroundColor Cyan
    Write-Host "  2) Set main owner + extra owners" -ForegroundColor Cyan
    Write-Host "  3) No extra owners" -ForegroundColor Cyan
    $choice = Read-Host "Select [1-3] (Enter = 1)"
    if ($choice -notmatch '^[123]$') { $choice = "1" }

    $ownerMain = ""
    $ownerExtra = ""

    if ($choice -eq "2") {
        $ownerMain = Read-Host "Main owner username (global)"
        $ownerExtra = Read-Host "Extra owners (comma-separated, optional)"
    }

    Write-Host ("Owners: MAIN='{0}' EXTRA='{1}'" -f ($ownerMain -ne "" ? $ownerMain : "<none>"), ($ownerExtra -ne "" ? $ownerExtra : "<none>")) -ForegroundColor Magenta

    Write-Host "▶ STEP 5: Writing .env" -ForegroundColor Blue
    @"
DISCORD_TOKEN=$token
BOT_ID=$botId
OWNER_MAIN=$ownerMain
OWNER_EXTRA=$ownerExtra
PRIORITY_OWNER=yoruboku
"@ | Out-File -Encoding utf8 .env
    Write-Host "[✓] .env created" -ForegroundColor Green

    # Gemini login
    Write-Host "▶ STEP 6: Gemini login" -ForegroundColor Blue
    Write-Host "[*] Launching Chromium persistent profile..." -ForegroundColor Cyan

    $code = @"
from playwright.sync_api import sync_playwright
import os

os.makedirs('playwright_data', exist_ok=True)

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context('playwright_data', headless=False)
    page = ctx.new_page()
    page.goto('https://gemini.google.com')
    print('\\n────────────────────────────────────────────')
    print('  Log in to GEMINI in the opened browser.')
    print('  Take your time. When fully logged in,')
    print('  close the browser window to continue.')
    print('────────────────────────────────────────────\\n')
    ctx.wait_for_event('close', timeout=900000)
"@

    & $PY -c $code

    Run-Bot
}

# Check existing install
$hasInstall = (Test-Path "venv" -PathType Container) -and (Test-Path ".env")

if ($hasInstall) {
    Write-Host ""
    Write-Host "VITO Launcher" -ForegroundColor Cyan
    Write-Host "  1) Run VITO (default)" -ForegroundColor Gray
    Write-Host "  2) New install / reinstall" -ForegroundColor Gray
    Write-Host "  3) Exit" -ForegroundColor Gray
    $sel = Read-Host "Select [1-3] (Enter = 1)"

    switch ($sel) {
        "2" { Do-Install }
        "3" { Write-Host "Exiting VITO installer." -ForegroundColor Yellow; exit 0 }
        default { Run-Bot }
    }
} else {
    Write-Host "[!] No existing installation found. Running full install..." -ForegroundColor Yellow
    Do-Install
}
