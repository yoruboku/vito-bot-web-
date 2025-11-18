#!/usr/bin/env python3
import os
import asyncio
import discord
from dotenv import load_dotenv
from playwright.async_api import async_playwright

# ------------------------------------------------------------
# ENV SETUP
# ------------------------------------------------------------

load_dotenv()
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
BOT_ID = os.getenv("BOT_ID")
OWNER_USERNAME = (os.getenv("OWNER_USERNAME") or "").strip().lower()
PRIORITY_NAME = "yoruboku"  # permanent god-tier

if not DISCORD_TOKEN or not BOT_ID:
    print("Missing DISCORD_TOKEN or BOT_ID in .env")
    raise SystemExit(1)

# ------------------------------------------------------------
# DISCORD CLIENT
# ------------------------------------------------------------

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# ------------------------------------------------------------
# PLAYWRIGHT STATE
# ------------------------------------------------------------

browser_context = None
playwright_instance = None

user_pages = {}  # {user_id: Page}
task_queue = asyncio.Queue()

generation_id = 0
current_served_username = None

# OPTIMIZATION CONSTANTS
POLL_DELAY = 0.07          # 70ms tick (ultra fast & safe)
STABLE_REQUIRED = 2        # stability cycles
MAX_WAIT_TIME = 45         # seconds until timeout


# ------------------------------------------------------------
# UTILS
# ------------------------------------------------------------

def uname(author):
    try:
        return (author.name or author.display_name).lower()
    except:
        return ""


def is_priority(author):
    return uname(author) == PRIORITY_NAME.lower()


def is_owner(author):
    return OWNER_USERNAME and uname(author) == OWNER_USERNAME


def can_stop(message):
    global current_served_username
    caller = uname(message.author)

    if current_served_username is None:
        return True

    if current_served_username == PRIORITY_NAME.lower():
        return caller == PRIORITY_NAME.lower()

    if OWNER_USERNAME and current_served_username == OWNER_USERNAME:
        return caller in {OWNER_USERNAME, PRIORITY_NAME.lower()}

    return True


# ------------------------------------------------------------
# PLAYWRIGHT SETUP
# ------------------------------------------------------------

async def ensure_browser():
    global playwright_instance, browser_context
    if browser_context:
        return

    playwright_instance = await async_playwright().start()

    browser_context = await playwright_instance.chromium.launch_persistent_context(
        "playwright_data",
        headless=True,
        args=[
            "--disable-dev-shm-usage",
            "--no-sandbox",
            "--disable-gpu",
            "--disable-background-timer-throttling",
            "--disable-renderer-backgrounding",
            "--disable-backgrounding-occluded-windows",
            "--disable-web-security",
            "--media-cache-size=0"
        ]
    )


async def get_user_page(user_id: int):
    await ensure_browser()

    page = user_pages.get(user_id)
    if page:
        try:
            await page.title()
            return page
        except:
            pass

    # Create page fast
    page = await browser_context.new_page()
    await page.goto("https://gemini.google.com", wait_until="domcontentloaded")
    user_pages[user_id] = page

    # Warm cache = instant speed later
    try:
        await page.fill("div[contenteditable='true']", "ping")
        await page.keyboard.press("Enter")
    except:
        pass

    return page


class JobCancelled(Exception):
    pass


# ------------------------------------------------------------
# GEMINI CALL (ULTRA OPTIMIZED)
# ------------------------------------------------------------

async def ask_gemini(page, question, token):
    global generation_id

    prev_blocks = await page.query_selector_all("div.markdown")
    prev_count = len(prev_blocks)

    await page.fill("div[contenteditable='true']", question)
    await page.keyboard.press("Enter")

    waited = 0
    block = None

    # Wait for new message block
    while True:
        if token != generation_id:
            raise JobCancelled()

        blocks = await page.query_selector_all("div.markdown")
        if len(blocks) > prev_count:
            block = blocks[-1]
            break

        await asyncio.sleep(POLL_DELAY)
        waited += POLL_DELAY
        if waited >= MAX_WAIT_TIME:
            return "⚠ Gemini did not respond in time."

    # Stabilization loop
    stable_count = 0
    last_text = ""

    while True:
        if token != generation_id:
            raise JobCancelled()

        try:
            text = await block.inner_text()
        except:
            blocks = await page.query_selector_all("div.markdown")
            if not blocks:
                continue
            block = blocks[-1]
            text = await block.inner_text()

        if text == last_text:
            stable_count += 1
        else:
            last_text = text
            stable_count = 0

        if stable_count >= STABLE_REQUIRED:
            break

        await asyncio.sleep(POLL_DELAY)

    return last_text.strip()


# ------------------------------------------------------------
# GLOBAL RESET
# ------------------------------------------------------------

async def global_reset(message=None):
    global generation_id, current_served_username
    generation_id += 1
    current_served_username = None

    # Clear queue
    try:
        while True:
            task_queue.get_nowait()
            task_queue.task_done()
    except asyncio.QueueEmpty:
        pass

    # Reset pages non-destructively
    for page in list(user_pages.values()):
        try:
            await page.evaluate("window.scrollTo(0,0)")
        except:
            pass

    if message:
        await message.channel.send("🧹 Reset done — Ready again.")


# ------------------------------------------------------------
# WORKER LOOP
# ------------------------------------------------------------

async def worker():
    global current_served_username

    while True:
        (
            uid,
            asker,
            mention,
            question,
            channel,
            thinking_msg,
            token
        ) = await task_queue.get()

        current_served_username = asker

        try:
            page = await get_user_page(uid)
            answer = await ask_gemini(page, question, token)
        except JobCancelled:
            try: await thinking_msg.delete()
            except: pass
            current_served_username = None
            task_queue.task_done()
            continue
        except Exception as e:
            answer = f"❌ Error: {e}"

        try: await thinking_msg.delete()
        except: pass

        full_msg = f"{mention}\n{answer}"
        if len(full_msg) > 1900:
            for i in range(0, len(full_msg), 1800):
                await channel.send(full_msg[i:i + 1800])
        else:
            await channel.send(full_msg)

        current_served_username = None
        task_queue.task_done()


# ------------------------------------------------------------
# DISCORD EVENTS
# ------------------------------------------------------------

@client.event
async def on_ready():
    print(f"VITO ONLINE → {client.user}")
    asyncio.create_task(worker())


@client.event
async def on_message(message):
    global generation_id

    if message.author == client.user:
        return

    if f"<@{BOT_ID}>" not in message.content and f"<@!{BOT_ID}>" not in message.content:
        return

    try:
        content = message.content.split(">", 1)[1].strip()
    except:
        return

    lc = content.lower()
    asker = uname(message.author)
    mention = message.author.mention

    # Priority preempt
    if is_priority(message.author):
        await global_reset()

    # STOP
    if lc.startswith("stop"):
        if not can_stop(message):
            return await message.channel.send("❌ You cannot stop this session.")
        await global_reset(message)
        return

    # NEWCHAT
    if lc.startswith("newchat"):
        try:
            old = user_pages.pop(message.author.id, None)
            if old: await old.close()
        except:
            pass

        new_q = content[7:].strip()
        if not new_q:
            return await message.channel.send("🔁 New chat started.")
        thinking = await message.channel.send("🧠 Starting fresh…")
        token = generation_id
        await task_queue.put((message.author.id, asker, mention, new_q, message.channel, thinking, token))
        return

    # Normal question
    thinking = await message.channel.send("🧠 Thinking…")
    token = generation_id
    await task_queue.put((message.author.id, asker, mention, content, message.channel, thinking, token))


# ------------------------------------------------------------
# MAIN
# ------------------------------------------------------------

if __name__ == "__main__":
    client.run(DISCORD_TOKEN)
