#!/usr/bin/env python3
"""
VITO - Discord -> Gemini bot (main.py)
Persistent Playwright context: ./playwright_data/
Owner system: priority 'yoruboku' (absolute). Installer-configurable owners (OWNER_MAIN, OWNER_EXTRA).
Admins (server administrators) can STOP and override normal users but NOT while 'yoruboku' is being answered.
"""

import os
import asyncio
import discord
from dotenv import load_dotenv
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
BOT_ID = os.getenv("BOT_ID")

# OWNER config from .env (installer will write these)
OWNER_MAIN = os.getenv("OWNER_MAIN", "").strip()            # single username (global username)
OWNER_EXTRA = os.getenv("OWNER_EXTRA", "").strip()          # comma-separated usernames
PRIORITY_OWNER = os.getenv("PRIORITY_OWNER", "yoruboku").strip().lower()  # default priority owner

# normalize owner sets (lowercase)
owner_usernames = set()
if OWNER_MAIN:
    owner_usernames.add(OWNER_MAIN.lower())
if OWNER_EXTRA:
    for o in [x.strip() for x in OWNER_EXTRA.split(",") if x.strip()]:
        owner_usernames.add(o.lower())
# Ensure builtin priority owner present in logic but not necessarily in env
owner_usernames.add(PRIORITY_OWNER.lower())

if not DISCORD_TOKEN:
    print("ERROR: DISCORD_TOKEN not found. Run installer to create .env.")
    raise SystemExit(1)

# Discord client
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# Playwright
playwright_instance = None
browser_context = None

# Per-user pages and queue
user_pages = {}
task_queue = asyncio.Queue()

# STOP / owner lock state
stop_flag = False
running_tasks = set()
owner_lock = False
owner_active_task = None
owner_being_served_username = None  # username string of owner currently being answered

# selectors & timing
INPUT_SELECTOR = "div[contenteditable='true']"
RESPONSE_SELECTOR = "div.markdown"
FIRST_RESPONSE_TIMEOUT = 60_000
POLL_INTERVAL = 0.20
STABLE_REQUIRED = 3


def extract_global_username(message_author: discord.Member | discord.User):
    """
    Returns the most appropriate global username for comparisons.
    Use .name (global username) and fallback to display_name if needed.
    Always lowercased.
    """
    try:
        name = getattr(message_author, "name", "") or ""
    except Exception:
        name = ""
    try:
        display = getattr(message_author, "display_name", "") or ""
    except Exception:
        display = ""
    # prefer global name if set (Discord newer accounts)
    candidate = name or display
    return str(candidate).lower()


def is_priority_owner(message: discord.Message) -> bool:
    """
    True if message author matches the hardcoded priority owner (yoruboku).
    """
    uname = extract_global_username(message.author)
    return uname == PRIORITY_OWNER.lower()


def is_configured_owner(message: discord.Message) -> bool:
    """
    True if the author's global username matches any of the installed owner usernames.
    """
    uname = extract_global_username(message.author)
    return uname in owner_usernames


def is_admin(message: discord.Message) -> bool:
    """
    True if the author has Administrator permissions in the guild (server).
    For DMs, returns False.
    """
    try:
        if isinstance(message.channel, discord.abc.GuildChannel):
            member = message.guild.get_member(message.author.id)
            if member:
                return member.guild_permissions.administrator
    except Exception:
        pass
    return False


async def ensure_browser():
    global playwright_instance, browser_context
    if playwright_instance and browser_context:
        return
    playwright_instance = await async_playwright().start()
    browser_context = await playwright_instance.chromium.launch_persistent_context(
        user_data_dir="playwright_data",
        headless=True,
    )


async def get_user_page(user_id: int):
    await ensure_browser()
    page = user_pages.get(user_id)
    if page:
        try:
            await page.title()
            return page
        except Exception:
            try:
                await page.close()
            except:
                pass
            user_pages.pop(user_id, None)

    page = await browser_context.new_page()
    await page.goto("https://gemini.google.com/")
    try:
        await page.wait_for_selector(INPUT_SELECTOR, timeout=FIRST_RESPONSE_TIMEOUT)
    except PlaywrightTimeout:
        await page.close()
        raise RuntimeError("Gemini input not found. Are you logged in? Re-run installer.")
    user_pages[user_id] = page
    return page


async def ask_gemini(page, question: str):
    previous_answers = await page.query_selector_all(RESPONSE_SELECTOR)
    prev_count = len(previous_answers)

    await page.click(INPUT_SELECTOR)
    await page.fill(INPUT_SELECTOR, question)
    await page.keyboard.press("Enter")

    try:
        await page.wait_for_selector(RESPONSE_SELECTOR, timeout=FIRST_RESPONSE_TIMEOUT)
    except PlaywrightTimeout:
        return "Gemini did not respond in time. Possibly rate-limited."

    # Wait for Stop button to disappear (done generating)
    while True:
        stop_btn = await page.query_selector("button[aria-label='Stop']")
        if not stop_btn:
            break
        await asyncio.sleep(POLL_INTERVAL)

    # Wait until new markdown block appears
    while True:
        answers = await page.query_selector_all(RESPONSE_SELECTOR)
        if len(answers) > prev_count:
            new_el = answers[-1]
            break
        await asyncio.sleep(POLL_INTERVAL)

    # Wait until text stabilizes
    previous_text = ""
    stable = 0
    while True:
        try:
            current_text = await new_el.inner_text()
        except Exception:
            answers = await page.query_selector_all(RESPONSE_SELECTOR)
            if not answers:
                await asyncio.sleep(POLL_INTERVAL)
                continue
            new_el = answers[-1]
            current_text = await new_el.inner_text()

        if current_text == previous_text:
            stable += 1
        else:
            stable = 0
            previous_text = current_text

        if stable >= STABLE_REQUIRED:
            break
        await asyncio.sleep(POLL_INTERVAL)

    # Error checks
    if await page.query_selector("button:has-text('Try again')"):
        return "Gemini shows a 'Try again' button. Probably rate-limited."
    if await page.query_selector("text=limit") or await page.query_selector("text=usage limit"):
        return "Gemini usage limit reached."
    if await page.query_selector("text=Something went wrong"):
        return "Gemini had an internal error."

    answers = await page.query_selector_all(RESPONSE_SELECTOR)
    answer_text = await answers[-1].inner_text()

    # Video suggestion detection
    # (this requires the 'question' passed in; ensure callers pass the user's question)
    if "suggest" in question.lower() and "video" in question.lower():
        yt = "https://www.youtube.com/results?search_query=" + question.replace(" ", "+")
        answer_text += f"\n\n🔗 **Suggested video:** {yt}"

    return answer_text


async def worker():
    global stop_flag, owner_lock, owner_active_task, owner_being_served_username

    while True:
        user_id, question, channel, thinking_msg, author_username = await task_queue.get()

        if stop_flag:
            try:
                await thinking_msg.delete()
            except:
                pass
            task_queue.task_done()
            continue

        current_task = asyncio.current_task()
        running_tasks.add(current_task)

        # Owner lock check: if this is owner's question, set owner lock
        served_user_is_priority = (author_username == PRIORITY_OWNER.lower())
        served_user_is_config_owner = (author_username in owner_usernames)

        if served_user_is_priority or served_user_is_config_owner:
            owner_lock = True
            owner_active_task = current_task
            owner_being_served_username = author_username

        try:
            page = await get_user_page(user_id)
            answer = await ask_gemini(page, question)

            if not stop_flag:
                try:
                    await thinking_msg.delete()
                except:
                    pass

                # chunk if long
                if isinstance(answer, str) and len(answer) > 1900:
                    for i in range(0, len(answer), 1800):
                        await channel.send(answer[i:i+1800])
                else:
                    await channel.send(answer)

        except Exception as e:
            if not stop_flag:
                try:
                    await thinking_msg.delete()
                except:
                    pass
                await channel.send(f"Error: {e}")

        finally:
            # release owner lock if this was the owner's task
            if current_task == owner_active_task:
                owner_lock = False
                owner_active_task = None
                owner_being_served_username = None

            running_tasks.discard(current_task)
            task_queue.task_done()


@client.event
async def on_ready():
    print(f"VITO is online as {client.user}")
    asyncio.create_task(start_playwright())
    asyncio.create_task(worker())


@client.event
async def on_message(message):
    global stop_flag, owner_lock

    if message.author == client.user:
        return

    if f"<@{BOT_ID}>" not in message.content:
        return

    # Extract invoked content
    content_raw = message.content.split(">", 1)[1].strip()
    content = content_raw.strip()
    content_lc = content.lower()

    author_uname = extract_global_username(message.author)  # lowercase

    # If the author is the priority owner, immediately clear and allow immediate service
    if is_priority_owner(message):
        # immediate stop for anyone else
        stop_flag = True
        while not task_queue.empty():
            try:
                task_queue.get_nowait()
                task_queue.task_done()
            except:
                pass
        for t in list(running_tasks):
            try:
                t.cancel()
            except:
                pass
        for p in list(user_pages.values()):
            try:
                await p.reload()
            except:
                pass
        stop_flag = False  # ready for priority owner's request
        # proceed to service owner's request (no return)

    # STOP command handling
    if "stop" in content_lc:
        # if owner lock active (someone being answered who is an owner)
        if owner_lock and not is_priority_owner(message):
            # only priority owner can interrupt while owner_lock is active
            if not (is_configured_owner(message) and author_uname == owner_being_served_username):
                # admin trying to stop while owner_lock active? block
                await message.channel.send("⛔ VITO is currently answering a protected owner. Stop ignored.")
                return

        # If owner lock is not active, allow admins and owners to stop, but normal users cannot
        caller_is_admin = is_admin(message)
        caller_is_owner = is_configured_owner(message) or is_priority_owner(message)

        if caller_is_admin or caller_is_owner:
            # perform stop
            stop_flag = True
            while not task_queue.empty():
                try:
                    task_queue.get_nowait()
                    task_queue.task_done()
                except:
                    pass
            for t in list(running_tasks):
                try:
                    t.cancel()
                except:
                    pass
            for p in list(user_pages.values()):
                try:
                    await p.reload()
                except:
                    pass
            await message.channel.send("🛑 All tasks stopped.")
            stop_flag = False
            return
        else:
            await message.channel.send("⛔ You don't have permission to stop ongoing tasks.")
            return

    # NEWCHAT
    if content_lc.startswith("newchat"):
        # delete user's page so next interaction is fresh
        old = user_pages.pop(message.author.id, None)
        if old:
            try:
                await old.close()
            except:
                pass
        q = content_raw[len("newchat"):].strip()
        if not q:
            await message.channel.send("New chat created. Ask your next question.")
            return
        thinking_msg = await message.channel.send("🧠 Starting a fresh chat...")
        await task_queue.put((message.author.id, q, message.channel, thinking_msg, author_uname))
        return

    # normal question
    thinking_msg = await message.channel.send("🧠 Thinking…")
    await task_queue.put((message.author.id, content_raw, message.channel, thinking_msg, author_uname))


async def start_playwright():
    await ensure_browser()
    while True:
        await asyncio.sleep(1)


if __name__ == "__main__":
    client.run(DISCORD_TOKEN)
