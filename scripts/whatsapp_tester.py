"""
WhatsApp Agent Tester
Automated conversation tester for TCM Jessica agent.
Sends RESTART, then simulates a patient consultation.
Logs full conversation for analysis.

Usage:
  1. CLOSE Google Chrome completely first
  2. Run: python3 scripts/whatsapp_tester.py
  3. Chrome will open with your existing WhatsApp Web session (no QR needed)
"""

import asyncio
import json
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path

import anthropic
from playwright.async_api import async_playwright

# ── Config ────────────────────────────────────────────────────────────────────
AGENT_NUMBER = "+852 5241 7448"
CHROME_PROFILE_DIR = os.path.expanduser(
    "~/Library/Application Support/Google/Chrome"
)
CHROME_PROFILE = "Default"          # shivonnekhoo@gmail.com
CHROME_DEBUG_PORT = 9222
LOG_DIR = Path(__file__).parent.parent / "data" / "test_logs"
MAX_TURNS = 20                       # safety cap
SILENCE_WINDOW = 4.0                 # seconds of no new msgs = agent done sending
REPLY_PAUSE = 1.5                    # pause before we type our reply (feels human)

PATIENT_SYSTEM_PROMPT = """You are a patient consulting a Traditional Chinese Medicine (TCM) WhatsApp chatbot.

Your background:
- 32-year-old woman named Amy
- Main complaint: skin itching (皮肤痒), especially on arms and back, worse at night
- Also: slightly dry skin, sometimes feels warm/flushed
- HK local, mix Cantonese and Mandarin is fine
- Heard about TCM from a friend, curious but slightly skeptical

Your job:
- Respond naturally as this patient would
- Answer the bot's questions honestly based on your skin itching symptoms
- Keep replies SHORT (1-3 sentences max) — this is WhatsApp
- If asked your name → "Amy"
- If asked your age → "32"
- Be slightly hesitant but cooperative
- Do NOT push for appointment — let the bot lead you there naturally
- Do NOT break character

Reply ONLY with what Amy would say. Nothing else."""

# Fixed opening messages sent in sequence before dynamic replies
FIXED_OPENERS = [
    "了解中医",
    "最近有感觉皮肤痒痒的",
]


# ── Logging ───────────────────────────────────────────────────────────────────

def setup_log() -> tuple[Path, list]:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = LOG_DIR / f"test_{ts}.json"
    return log_file, []


def log_msg(conversation: list, role: str, text: str) -> None:
    entry = {"role": role, "text": text, "time": datetime.now().isoformat()}
    conversation.append(entry)
    prefix = "🤖 AGENT  " if role == "agent" else "👤 PATIENT"
    print(f"\n{prefix}: {text}")


def save_log(log_file: Path, conversation: list) -> None:
    with open(log_file, "w", encoding="utf-8") as f:
        json.dump(conversation, f, ensure_ascii=False, indent=2)
    print(f"\n📝 Saved: {log_file}")


# ── WhatsApp helpers ──────────────────────────────────────────────────────────

async def open_chat(page, number: str) -> bool:
    """Search for the contact and open the chat."""
    print(f"\n🔍 Opening chat with {number}...")

    # Click the search input
    search = page.locator('input[data-tab="3"]')
    await search.wait_for(timeout=30_000)
    await search.click()
    await asyncio.sleep(0.5)
    await search.fill(number)
    await asyncio.sleep(2)

    # Click the first result
    try:
        first_result = page.locator('[data-testid="cell-frame-container"]').first
        await first_result.wait_for(timeout=8_000)
        await first_result.click()
        await asyncio.sleep(1.5)
        print(f"✅ Chat open")
        return True
    except Exception:
        print(f"⚠️  Contact not found in search. Make sure you've chatted before.")
        return False


async def send(page, text: str) -> None:
    """Type and send a message."""
    box = page.locator('div[contenteditable="true"][data-tab="10"]')
    await box.wait_for(timeout=10_000)
    await box.click()
    await asyncio.sleep(0.3)
    await page.keyboard.type(text, delay=25)
    await asyncio.sleep(0.3)
    await page.keyboard.press("Enter")
    await asyncio.sleep(0.5)
    print(f"✉️  Sent: {text[:80]}{'…' if len(text) > 80 else ''}")


async def send_image(page, image_path: str) -> None:
    """Send an image file in the current WhatsApp chat."""
    print(f"🖼️  Sending image: {Path(image_path).name}")
    # WhatsApp Web has a hidden file input — set the file directly
    # First click the attach button to reveal the input
    attach_btn = page.locator('span[data-icon="plus"]').first
    if not await attach_btn.count():
        attach_btn = page.locator('div[title="Attach"]')
    await attach_btn.click()
    await asyncio.sleep(0.8)

    # Set file on the image/video file input
    file_input = page.locator('input[accept*="image/"]').first
    await file_input.set_input_files(image_path)
    await asyncio.sleep(1.5)

    # Press Enter to send
    await page.keyboard.press("Enter")
    await asyncio.sleep(1)
    print("   Image sent.")


async def get_incoming_texts(page) -> list[str]:
    """Return all visible incoming message texts (agent bubbles).
    Uses page.evaluate() for atomic DOM access — avoids stale locator issues.
    """
    raw_texts: list[str] = await page.evaluate("""() => {
        const msgs = document.querySelectorAll('div[class*="message-in"]');
        return Array.from(msgs)
            .map(el => el.innerText.trim())
            .filter(t => t.length > 2);
    }""")
    return raw_texts


async def wait_for_agent_burst(
    page,
    baseline_count: int,
    first_timeout: int = 90,
    silence: float = SILENCE_WINDOW,
) -> tuple[str | None, int]:
    """
    Wait for the agent to finish sending its turn (may be multiple bubbles).
    Strategy:
      1. Wait up to `first_timeout` s for the first new message.
      2. Once the first arrives, keep collecting for `silence` seconds of no new msgs.
      3. Return combined text + new baseline count.
    """
    deadline = time.time() + first_timeout
    first_arrived = False
    last_change_time = time.time()
    current_count = baseline_count

    while True:
        texts = await get_incoming_texts(page)
        new_count = len(texts)

        if new_count > current_count:
            current_count = new_count
            last_change_time = time.time()
            if not first_arrived:
                first_arrived = True
                print(f"   ↳ First reply received, collecting burst…")

        if first_arrived:
            # Once we have messages, wait for silence window
            if time.time() - last_change_time >= silence:
                new_texts = texts[baseline_count:]
                combined = "\n".join(t.strip() for t in new_texts if t.strip())
                return combined, current_count

        elif time.time() > deadline:
            print("⏰ Timeout — no reply received.")
            return None, current_count

        await asyncio.sleep(0.8)


# ── AI patient reply ──────────────────────────────────────────────────────────

def patient_reply(
    client: anthropic.Anthropic,
    conversation: list,
    agent_text: str,
) -> str:
    """Generate a natural patient reply using Claude Haiku."""
    messages: list[dict] = []
    for entry in conversation:
        if entry["role"] == "agent":
            messages.append({"role": "user", "content": entry["text"]})
        elif entry["role"] == "patient":
            messages.append({"role": "assistant", "content": entry["text"]})

    messages.append({"role": "user", "content": agent_text})

    resp = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=200,
        system=PATIENT_SYSTEM_PROMPT,
        messages=messages,
    )
    return resp.content[0].text.strip()


# ── Main ──────────────────────────────────────────────────────────────────────

TEMP_PROFILE_DIR = "/tmp/chrome-wa-test"
TONGUE_IMAGE = str(Path(__file__).parent.parent / "data" / "media" / "tongue_test.png")

# Keywords that signal the agent is asking for a tongue photo
TONGUE_REQUEST_SIGNALS = [
    "舌頭", "舌头", "舌苔", "拍相", "拍張", "照片", "相片",
    "send", "tongue", "photo", "image", "圖片",
]


def launch_chrome_with_debug() -> subprocess.Popen:
    """
    Copy the real Chrome Default profile to a temp dir, then launch Chrome
    with remote debugging. Chrome refuses --remote-debugging-port on its own
    default data dir, but allows it on any other path.
    """
    import shutil

    chrome_bin = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"
    src = os.path.expanduser("~/Library/Application Support/Google/Chrome/Default")

    print(f"\n📋 Copying Chrome profile to {TEMP_PROFILE_DIR}…")
    if os.path.exists(TEMP_PROFILE_DIR):
        shutil.rmtree(TEMP_PROFILE_DIR)
    os.makedirs(f"{TEMP_PROFILE_DIR}/Default", exist_ok=True)
    shutil.copytree(src, f"{TEMP_PROFILE_DIR}/Default", dirs_exist_ok=True)
    print(f"   Done.")

    cmd = [
        chrome_bin,
        f"--remote-debugging-port={CHROME_DEBUG_PORT}",
        "--profile-directory=Default",
        f"--user-data-dir={TEMP_PROFILE_DIR}",
        "--no-first-run",
        "--no-default-browser-check",
        "--start-maximized",
        "https://web.whatsapp.com",
    ]
    print(f"🚀 Launching Chrome with debug port {CHROME_DEBUG_PORT}…")
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"   Chrome PID: {proc.pid}")
    return proc


async def main() -> None:
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    client = anthropic.Anthropic(api_key=api_key) if api_key else None
    if not client:
        print("⚠️  ANTHROPIC_API_KEY missing — patient replies will be static fallback.")

    log_file, conversation = setup_log()

    async with async_playwright() as p:
        print("\n🚀 Launching headless Chromium with copied profile…")

        # Use the profile copy we already made at /tmp/chrome-wa-test
        # headless=True = no visible window, no focus stealing
        # Use system Chrome (not bundled Chromium) so WhatsApp Web
        # recognises the browser version. headless=True = no window.
        context = await p.chromium.launch_persistent_context(
            user_data_dir=TEMP_PROFILE_DIR,
            channel="chrome",
            headless=True,
            args=[
                "--profile-directory=Default",
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-blink-features=AutomationControlled",
            ],
        )

        page = await context.new_page()
        await page.goto("https://web.whatsapp.com")

        print("⏳ Waiting for WhatsApp Web to load…")
        try:
            await page.wait_for_selector('input[data-tab="3"]', timeout=90_000)
            print("✅ WhatsApp Web ready (headless — no window)!")
        except Exception:
            # Session might have expired — save screenshot for debug
            await page.screenshot(path="/tmp/wa_headless_debug.png")
            print("❌ WhatsApp didn't load. Screenshot: /tmp/wa_headless_debug.png")
            print("   Session may have expired — need to re-login with visible Chrome.")
            await context.close()
            return

        await asyncio.sleep(1.5)

        # Open the agent chat
        if not await open_chat(page, AGENT_NUMBER):
            await context.close()
            return

        # ── Wait for chat history to fully load, then lock baseline ─────────────
        print("⏳ Letting chat history settle (3s)…")
        await asyncio.sleep(3)
        baseline = len(await get_incoming_texts(page))
        await asyncio.sleep(2)
        check = len(await get_incoming_texts(page))
        if check != baseline:
            await asyncio.sleep(3)
            baseline = len(await get_incoming_texts(page))
        print(f"   Baseline locked at {baseline} messages.")

        # ── Fixed opening sequence ────────────────────────────────────────────
        for opener in FIXED_OPENERS:
            await send(page, opener)
            log_msg(conversation, "patient", opener)
            print(f"\n⏳ Waiting for agent response…")
            reply_text, baseline = await wait_for_agent_burst(page, baseline)
            if reply_text:
                log_msg(conversation, "agent", reply_text)
            await asyncio.sleep(REPLY_PAUSE)

        # ── Dynamic conversation loop ─────────────────────────────────────────
        for turn in range(MAX_TURNS):
            print(f"\n⏳ [{turn + 1}/{MAX_TURNS}] Waiting for agent burst…")
            reply_text, baseline = await wait_for_agent_burst(page, baseline)

            if not reply_text:
                print("🛑 No reply — ending test.")
                break

            log_msg(conversation, "agent", reply_text)

            # Detect natural end of conversation
            end_signals = ["再見", "bye", "appointment confirmed", "預約成功", "感謝你", "thank you"]
            if any(sig.lower() in reply_text.lower() for sig in end_signals):
                print("\n✅ Conversation reached a natural end.")
                break

            await asyncio.sleep(REPLY_PAUSE)

            # If agent is asking for tongue photo, send the image
            asking_for_tongue = any(
                sig.lower() in reply_text.lower() for sig in TONGUE_REQUEST_SIGNALS
            )
            if asking_for_tongue and os.path.exists(TONGUE_IMAGE):
                await send_image(page, TONGUE_IMAGE)
                log_msg(conversation, "patient", "[sent tongue photo]")
            else:
                # Generate and send patient reply
                if client:
                    p_reply = patient_reply(client, conversation, reply_text)
                else:
                    p_reply = "好的，請繼續"
                await send(page, p_reply)
                log_msg(conversation, "patient", p_reply)

        # ── Done ──────────────────────────────────────────────────────────────
        save_log(log_file, conversation)
        print("\n" + "=" * 60)
        print("📊 REVIEW CHECKLIST:")
        print("  1. Conversation logic reasonable / natural?")
        print("  2. Agent recommended products?")
        print("  3. Agent led to appointment booking?")
        print("=" * 60)
        print("\n✅ Test complete. Closing headless browser.")
        await context.close()


if __name__ == "__main__":
    asyncio.run(main())
