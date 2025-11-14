import discord
import asyncio
from playwright.async_api import async_playwright

DISCORD_TOKEN = "MTQzODY2MDE3NzU1NjY2ODUxNw.GrTlIq.LXSO1RXpXOGsOY8ZyxoFQuT_EztdUwE5D9iBmA"
BOT_ID = "1438660177556668517"   # for example: 123456789012345678

intents = discord.Intents.default()
intents.message_content = True   # REQUIRED for reading messages
intents.messages = True          # optional but recommended

client = discord.Client(intents=intents)

browser_context = None
page = None

async def init_gemini(playwright):
    global browser_context, page

    browser_context = await playwright.chromium.launch_persistent_context(
        user_data_dir="playwright_data",  # saved login session
        headless=True
    )
    page = await browser_context.new_page()

    await page.goto("https://gemini.google.com/")
    await page.wait_for_selector("textarea[aria-label='Message Gemini']")

async def ask_gemini(question):
    await page.fill("textarea[aria-label='Message Gemini']", question)
    await page.keyboard.press("Enter")

    # wait for Gemini to respond
    await page.wait_for_selector("div.markdown", timeout=45000)

    answers = await page.query_selector_all("div.markdown")
    return await answers[-1].inner_text()

@client.event
async def on_ready():
    print(f"zom is alive as {client.user}")

    # launch Gemini in the background
    asyncio.create_task(start_playwright())

async def start_playwright():
    async with async_playwright() as playwright:
        await init_gemini(playwright)
        while True:
            await asyncio.sleep(1)  # keep browser running

@client.event
async def on_message(message):
    if message.author == client.user:
        return

    # check if zom is mentioned
    if f"<@{BOT_ID}>" in message.content:
        question = message.content.split(">", 1)[1].strip()
        if not question:
            await message.channel.send("Ask me something.")
            return

        await message.channel.send("🧠 Thinking…")

        try:
            answer = await ask_gemini(question)
            await message.channel.send(answer)
        except Exception as e:
            await message.channel.send(f"Error: {e}")

client.run(DISCORD_TOKEN)
