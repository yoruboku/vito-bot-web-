$PY = (Get-Command python -ErrorAction SilentlyContinue).Name
if (-not $PY) { Write-Host "Python not found"; exit 1 }
if (-not (Test-Path playwright_data)) { New-Item -ItemType Directory -Path playwright_data | Out-Null }
$code = @"
from playwright.sync_api import sync_playwright
import os, time
os.makedirs('playwright_data', exist_ok=True)
with sync_playwright() as p:
    context = p.chromium.launch_persistent_context(user_data_dir='playwright_data', headless=False)
    page = context.new_page()
    page.goto('https://gemini.google.com/')
    print('Open. Close window to exit.')
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    context.close()
"@
& $PY -c $code
