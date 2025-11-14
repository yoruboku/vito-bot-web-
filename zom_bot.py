import discord
import asyncio
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout

DISCORD_TOKEN = "MTQzODY2MDE3NzU1NjY2ODUxNw.GLgKGo.EKghT6qMAjdEQeutG9mpsr25BUvXPTKAvNWNcA"
BOT_ID = "1438660177556668517"

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

browser_context = None
user_pages = {}         # user_id -> Gemini page
task_queue = asyncio.Queue()

INPUT_SELECTOR = "div[contenteditable='true']"
RESPONSE_SELECTOR = "div.markdown"


# ---------------------------------------------------------
# INITIALIZE PLAYWRIGHT + PERSISTENT BROWSER
# ---------------------------------------------------------
async def init_browser(playwright):
    global browser_context

    browser_context = await playwright.chromium.launch_persistent_context(
        "playwright_data",
        headless=True
    )


async def get_user_page(user_id):
    """Each user gets their own Gemini chat tab."""
    global user_pages

    if user_id in user_pages:
        return user_pages[user_id]

    page = await browser_context.new_page()
    await page.goto("https://gemini.google.com/")
    await page.wait_for_selector(INPUT_SELECTOR, timeout=60000)

    user_pages[user_id] = page
    return page


# ---------------------------------------------------------
# GEMINI ASK FUNCTION
# ---------------------------------------------------------
async def ask_gemini(page, question):
    # click + type into the input
    await page.click(INPUT_SELECTOR)
    await page.fill(INPUT_SELECTOR, question)
    await page.keyboard.press("Enter")

    # wait for answer OR detect error
    try:
        await page.wait_for_selector(RESPONSE_SELECTOR, timeout=60000)
    except PlaywrightTimeout:
        return "Gemini did not respond in time. Might be rate-limited."

    # detect “Try again” or rate limit messages
    try_again = await page.query_selector("button:has-text('Try again')")
    over_limit = await page.query_selector("text=limit")
    error_box = await page.query_selector("text=Something went wrong")

    if try_again:
        return "Gemini shows a 'Try Again' button. Probably rate-limited."

    if over_limit:
        return "Gemini usage limit reached."

    if error_box:
        return "Gemini had an error."

    # otherwise return latest markdown response
    answers = await page.query_selector_all(RESPONSE_SELECTOR)
    return await answers[-1].inner_text()


# ---------------------------------------------------------
# QUEUE WORKER (so only one browser task runs at a time)
# ---------------------------------------------------------
async def worker():
    while True:
        user_id, question, channel, thinking_msg = await task_queue.get()
        try:
            page = await get_user_page(user_id)
            answer = await ask_gemini(page, question)
            await thinking_msg.delete()
            await channel.send(answer)
        except Exception as e:
            await thinking_msg.delete()
            await channel.send(f"Error: {e}")
        finally:
            task_queue.task_done()


# ---------------------------------------------------------
# DISCORD EVENTS
# ---------------------------------------------------------
@client.event
async def on_ready():
    print(f"zom is alive as {client.user}")

    asyncio.create_task(start_playwright())
    asyncio.create_task(worker())


@client.event
async def on_message(message):
    if message.author == client.user:
        return

    if f"<@{BOT_ID}>" in message.content:
        question = message.content.split(">", 1)[1].strip()

        thinking_msg = await message.channel.send("🧠 Thinking…")

        await task_queue.put((
            message.author.id,
            question,
            message.channel,
            thinking_msg
        ))


# ---------------------------------------------------------
# PLAYWRIGHT STARTUP
# ---------------------------------------------------------
async def start_playwright():
    async with async_playwright() as pw:
        await init_browser(pw)
        while True:
            await asyncio.sleep(1)


client.run(DISCORD_TOKEN)

