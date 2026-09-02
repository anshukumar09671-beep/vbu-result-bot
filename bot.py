import os
import json
import requests
from urllib.parse import urljoin
from playwright.sync_api import sync_playwright

VBU_URL = "https://www.vbu.ac.in/notice/result"

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

DATA_FILE = "seen.json"


def get_results():
    results = []

    print("🔎 VBU Result checking...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto(
            VBU_URL,
            wait_until="domcontentloaded",
            timeout=60000
        )

        page.wait_for_timeout(5000)

        links = page.locator("a[href]").all()

        for a in links:
            try:
                text = a.inner_text().strip()
                href = a.get_attribute("href")

                if not text or not href:
                    continue

                if "result" not in text.lower():
                    continue

                link = urljoin(VBU_URL, href)

                results.append({
                    "title": text,
                    "link": link
                })

            except Exception:
                continue

        browser.close()

    # Duplicate हटाना
    unique = []
    seen_links = set()

    for result in results:
        key = result["title"] + "|" + result["link"]

        if key not in seen_links:
            seen_links.add(key)
            unique.append(result)

    return unique


def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    response = requests.post(
        url,
        data={
            "chat_id": CHAT_ID,
            "text": message,
            "disable_web_page_preview": False
        },
        timeout=30
    )

    print("Telegram:", response.text)

    response.raise_for_status()


def load_seen():
    if not os.path.exists(DATA_FILE):
        return set()

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except Exception:
        return set()


def save_seen(seen):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(
            list(seen),
            f,
            ensure_ascii=False
        )
