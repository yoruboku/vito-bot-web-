#!/usr/bin/env python3
"""
VITO - Discord -> Gemini bot (main.py)
Uses Playwright persistent context stored in ./playwright_data/
"""

import os
import asyncio
import discord
from dotenv import load_dotenv
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

load_dotenv()

DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")
BOT_ID = os.getenv("BOT_ID")  # numeric id as string

if not DISCORD_TOKEN:
    print("ERROR: DISCORD_TOKEN not found. Run the installer to create a .env file or set DISCORD_TOKEN in the environment.")
    raise SystemExit(1)

# Discord client setup
intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# Playwright globals
playwright_instance = None
browser_context = None

# Per-user pages (user_id -> Page)
user_pages = {}
task_queue = asyncio.Queue()

# Selectors (update if Gemini UI changes)
INPUT_SELECTOR = "div[contenteditable='true']"
RESPONSE_SELECTOR = "div.markdown"

# Timeouts / tuning
FIRST_RESPONSE_TIMEOUT = 60_000
POLL_INTERVAL = 0.25
STABLE_REQUIRED = 3


async def ensure_browser():
    """Start playwright and persistent browser context if not running."""
    global playwright_instance, browser_context
    if playwright_instance and browser_context:
        return

    playwright_instance = await async_playwright().start()

    # persistent context uses user_data_dir so cookies/storage are shared with installer
    browser_context = await playwright_instance.chromium.launch_persistent_context(
        user_data_dir="playwright_data",
        headless=True,
    )


async def get_user_page(user_id: int):
    """Return a per-user page. Create new if missing."""
    await ensure_browser()

    # If page exists and is alive, return it
    page = user_pages.get(user_id)
    if page:
        try:
            await page.title()
            return page
        except Exception:
            try:
                await page.close()
            except Exception:
                pass
            user_pages.pop(user_id, None)

    # Create new page
    page = await browser_context.new_page()
    await page.goto("https://gemini.google.com/")
    # If input selector isn't present, likely not logged in
    try:
        await page.wait_for_selector(INPUT_SELECTOR, timeout=FIRST_RESPONSE_TIMEOUT)
    except PlaywrightTimeout:
        await page.close()
        raise RuntimeError("Gemini input not found - are you logged in? Re-run installer to login to Gemini.")
    user_pages[user_id] = page
    return page


async def ask_gemini(page, question: str):
    """Send a question and wait for Gemini to finish generating the full answer."""
    # Count existing answers
    previous_answers = await page.query_selector_all(RESPONSE_SELECTOR)
    prev_count = len(previous_answers)

    # Send the question
    await page.click(INPUT_SELECTOR)
    await page.fill(INPUT_SELECTOR, question)
    await page.keyboard.press("Enter")

    # Wait for any response to appear
    try:
        await page.wait_for_selector(RESPONSE_SELECTOR, timeout=FIRST_RESPONSE_TIMEOUT)
    except PlaywrightTimeout:
        return "Gemini did not respond in time. Possibly rate-limited."

    # Wait until Stop button disappears (Gemini finished streaming)
    # Use aria-label "Stop" detection; fallback to stability polling
    while True:
        stop_btn = await page.query_selector("button[aria-label='Stop']")
        if not stop_btn:
            break
        await asyncio.sleep(POLL_INTERVAL)

    # Now wait for the new element to appear (prev_count -> new count)
    while True:
        answers = await page.query_selector_all(RESPONSE_SELECTOR)
        if len(answers) > prev_count:
            new_el = answers[-1]
            break
        await asyncio.sleep(POLL_INTERVAL)

    # Wait until the new element's text stabilizes
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

    # Detect common errors / rate limits
    if await page.query_selector("button:has-text('Try again')"):
        return "Gemini shows a 'Try again' button. Probably rate-limited."
    if await page.query_selector("text=limit") or await page.query_selector("text=usage limit"):
        return "Gemini usage limit reached."
    if await page.query_selector("text=Something went wrong"):
        return "Gemini had an internal error."

    # Return final answer
    answers = await page.query_selector_all(RESPONSE_SELECTOR)
    return await answers[-1].inner_text()


async def worker():
    while True:
        user_id, question, channel, thinking_msg = await task_queue.get()
        try:
            page = await get_user_page(user_id)
            answer = await ask_gemini(page, question)
        except Exception as exc:
            try:
                await thinking_msg.delete()
            except Exception:
                pass
            await channel.send(f"Error while talking to Gemini: {exc}")
            task_queue.task_done()
            continue

        # Delete thinking message then send final answer
        try:
            await thinking_msg.delete()
        except Exception:
            pass

        # split long answers
        if isinstance(answer, str) and len(answer) > 1900:
            for i in range(0, len(answer), 1800):
                await channel.send(answer[i:i+1800])
        else:
            await channel.send(answer)

        task_queue.task_done()


@client.event
async def on_ready():
    print(f"VITO is online as {client.user}")
    # Start playwright and worker
    asyncio.create_task(start_playwright())
    asyncio.create_task(worker())


@client.event
async def on_message(message):
    # ignore self
    if message.author == client.user:
        return

    if f"<@{BOT_ID}>" not in message.content:
        return

    content = message.content.split(">", 1)[1].strip()

    # newchat command (create fresh chat for the user)
    if content.lower().startswith("newchat"):
        # remove old page and create new one on demand
        old = user_pages.pop(message.author.id, None)
        if old:
            try:
                await old.close()
            except Exception:
                pass

        question = content[len("newchat"):].strip()
        if not question:
            await message.channel.send("New chat created. Ask your question with `@VITO <question>`.")
            return

        thinking_msg = await message.channel.send("🧠 Starting a fresh chat...")
        await task_queue.put((message.author.id, question, message.channel, thinking_msg))
        return

    # normal message
    question = content
    thinking_msg = await message.channel.send("🧠 Thinking…")
    await task_queue.put((message.author.id, question, message.channel, thinking_msg))


async def start_playwright():
    # keep playwright alive
    await ensure_browser()
    while True:
        await asyncio.sleep(1)


if __name__ == "__main__":
    client.run(DISCORD_TOKEN)
