# 🌌 **VITO — Discord AI Web Bot (Gemini Web)**

![Logo](vito.png)

[![Python](https://img.shields.io/badge/python-3.11+-3776AB?logo=python&logoColor=white)]()
[![Playwright](https://img.shields.io/badge/playwright-1.44+-2EAD33?logo=playwright&logoColor=white)]()
[![License](https://img.shields.io/badge/license-MIT-red)]()
[![Made By](https://img.shields.io/badge/Made%20By-YoruBoku-blueviolet)]()

---

## ⭐ Overview

**VITO** is a self-hosted Discord AI bot that interacts with **Google Gemini** using Playwright web automation.  
No API keys, no usage fees — VITO extracts full Gemini responses directly from the browser.

---

## ✨ Features

- 💬 Responds when mentioned (`@VITO`)
- 🔁 Independent per-user chat sessions
- 🆕 `newchat` command resets personal context
- 🚫 Interrupt & stop active tasks (`@VITO stop`)
- 👑 Owner priority & admin override system
- 🧠 Reliable response completion detection
- 🔗 Video suggestion & YouTube auto-linking
- 🔒 Persistent login via Playwright storage
- 🖥 Cross‑platform installers (Linux/macOS & Windows)

> Note: Gemini interface changes may require future selector updates.

---

## 🧩 Requirements

- Python **3.11+**
- Git
- Discord Bot Token & Application ID
- Ability to log in to Gemini via Chromium popup

---

## 📥 Installation

### 1️⃣ Clone
```bash
git clone https://github.com/yoruboku/vito-bot.git
cd vito-bot
```

### 2️⃣ Run the Installer

#### Linux / macOS
```bash
chmod +x install.sh
./install.sh
```




### Installer Actions
| Step | Action |
|------|---------|
| 1 | Detect Python & create VENV |
| 2 | Install dependencies |
| 3 | Install Playwright Chromium |
| 4 | Ask for bot token & bot ID |
| 5 | Owner mode selection |
| 6 | Open Gemini login persistent browser |
| 7 | Save session & launch bot |

You will only need to log in once — future runs do not require login.

---

## 🛠 Discord Developer Setup

1. Open https://discord.com/developers/applications  
2. Create an **Application** → Add **Bot**
3. Enable **MESSAGE CONTENT INTENT**
4. Go to **OAuth2 → URL Generator**
5. Enable scopes:
   - `bot`
   - `applications.commands`
6. Permissions required:
   - View Channels
   - Send Messages
   - Read Message History
7. Copy **Bot Token** + **Application ID** for installer



---

## 🔑 Owner System

### Priority Owner (Built‑in)
The username **yoruboku** always has highest priority.

### Installer Options
```
1️⃣ Default (Only YoruBoku)
2️⃣ Set Owner A
3️⃣ Set Owner A + Owner B list
```

Owners gain:
- Interrupt control
- Faster queue priority
- Immune to normal user stop commands

Admins can stop normal users but **not** owners.

---

## 💬 Commands

| Command | Description |
|---------|-------------|
| `@VITO <question>` | Ask anything |
| `@VITO newchat` | Reset your chat session |
| `@VITO newchat <message>` | Reset + send new message |
| `@VITO stop` | Interrupt (owners/admins only) |

### Example
```
@VITO What is the fastest marine animal?
@VITO newchat
@VITO newchat Tell me a true crime story
@VITO stop
```

---

## 🔄 Updating

#### Linux/macOS
```bash
./update.sh
```

#### Windows
```powershell
.\update.ps1
```

---

## 🔐 Re‑login Gemini

If logout or session expiry occurs:

#### Linux/macOS
```bash
./open_gemini.sh
```

#### Windows
```powershell
.\open_gemini.ps1
```

---

## 📂 File Structure

```
/vito-bot
│
├─ main.py
├─ install.sh
├─ install.ps1
├─ update.sh
├─ update.ps1
├─ open_gemini.sh
├─ open_gemini.ps1
├─ requirements.txt
├─ README.md
├─ LICENSE
└─ playwright_data/ (auto-created)
```

---

## ⚠️ Disclaimer

- Gemini UI may change — this bot may require selector updates.
- Use responsibly and respect Discord/Google TOS.
- For educational + private automation only.

---

## 🧾 License

**MIT License © 2025 YoruBoku**  
Contact: **omenboku@gmail.com**

---

## Final Notes

VITO is fast, reliable, extensible, and fully free — no API limitations.  
If you'd like extra features, commands, or dashboard UI, just ask!

---

Made by Python using Yoruboku.
