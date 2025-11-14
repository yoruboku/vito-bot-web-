<#
install.ps1 — Interactive installer for Windows (PowerShell)
#>

function Write-Color {
    param([string]$Text, [string]$Color = "White")
    $colors = @{
        Red="Red"; Green="Green"; Yellow="Yellow"; Blue="Cyan"; White="White"
    }
    $c = $colors[$Color]
    Write-Host $Text -ForegroundColor $c
}

Write-Color "=== AIDC-Bot (Zom) Installer ===" "Green"

# Check python
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Color "Python not found. Install Python 3.9+ and re-run." "Red"; exit 1
}

# create venv
Write-Color "Creating virtual environment..." "Blue"
python -m venv venv

Write-Color "Activating venv..." "Blue"
Set-Location -Path (Get-Location)
& .\venv\Scripts\Activate.ps1

Write-Color "Upgrading pip and installing requirements..." "Blue"
python -m pip install --upgrade pip
pip install -r requirements.txt

# prompt token and id
function Read-NonEmpty([string]$prompt) {
    while ($true) {
        $val = Read-Host $prompt
        if ($val -and $val.Trim() -ne "") { return $val }
        Write-Color "Value cannot be empty. Try again." "Yellow"
    }
}

function Read-BotId() {
    while ($true) {
        $id = Read-Host "Enter your Discord Bot ID (numeric)"
        if ($id -match '^[0-9]+$') { return $id }
        Write-Color "Bot ID must be numeric. Try again." "Yellow"
    }
}

$token = Read-NonEmpty "Enter your Discord Bot Token"
$botid = Read-BotId

# create .env
$envText = "DISCORD_TOKEN=""$token""" + "`n" + "BOT_ID=""$botid"""
Set-Content -Path ".env" -Value $envText -Encoding UTF8
Write-Color ".env created." "Green"

Write-Color "Installing Playwright Chromium..." "Blue"
python -m playwright install chromium

Write-Color "Installation complete!" "Green"
Write-Color "Run the bot with: .\venv\Scripts\Activate.ps1 ; python zom_bot.py" "Blue"
