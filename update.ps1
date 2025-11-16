if (Test-Path .git) { git pull --rebase }
if (Test-Path venv) {
    & .\venv\Scripts\Activate.ps1
    pip install --upgrade pip
    pip install -r requirements.txt
    python -m playwright install chromium
    python main.py
} else {
    Write-Host "No venv found. Run install.ps1 first."
    exit 1
}
