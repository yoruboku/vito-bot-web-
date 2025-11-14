Write-Host "=== ZOM BOT INSTALLER ==="

if (-Not (Test-Path ".env")) {
    $token = Read-Host "Enter your Discord Token"
    $botid = Read-Host "Enter your Bot ID"

    Set-Content ".env" "DISCORD_TOKEN=$token`nBOT_ID=$botid"
}

Write-Host "Creating virtual environment..."
python -m venv venv

Write-Host "Installing dependencies..."
.\venv\Scripts\activate
pip install -r requirements.txt

Write-Host "Installing Playwright Chromium..."
playwright install chromium

Write-Host "Done!"
Write-Host "Run the bot using:"
Write-Host ".\venv\Scripts\activate && python zom_bot.py"
