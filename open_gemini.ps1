# Activate virtual env
if (Test-Path "venv\Scripts\Activate.ps1") {
    . "venv\Scripts\Activate.ps1"
} else {
    Write-Host "Virtual environment not found. Please run install.ps1 first."
    exit 1
}

$PY = (Get-Command python -ErrorAction SilentlyContinue).Name
if (-not $PY) { Write-Host "Python not found"; exit 1 }
if (-not (Test-Path playwright_data)) { New-Item -ItemType Directory -Path playwright_data | Out-Null }
$code = @"
from playwright.sync_api import sync_playwright
import os
os.makedirs('playwright_data', exist_ok=True)
with sync_playwright() as p:
    context = p.chromium.launch_persistent_context(user_data_dir='playwright_data', headless=False)
    page = context.new_page()
    page.goto('https://gemini.google.com/')
    print('Open. Close window to exit.')
    context.wait_for_event('close')
"@
& $PY -c $code
