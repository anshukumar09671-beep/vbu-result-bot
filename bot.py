import os
import json
import time
import requests
from playwright.sync_api import sync_playwright

VBU_URL = "https://www.vbu.ac.in/notice/result"

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

DATA_FILE = "seen.json"


def get_results():
    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        page.goto(VBU_URL, wait_until="domcontentloaded", timeout=30000)
        page.wait_for_timeout(5000)

        links = page.locator("a[href]").all()

        for a in links:
            try:
                text = a.inner_text().strip()
                href = a.get_attribute("href")

                if not text or not href:
                    continue

                if "result" in text.lower():
                    if href.startswith("/"):
                        href = "https://www.vbu.ac.in" + href

                    results.append({
                        "title": text,
                        "link": href
                    })

            except:
                continue

        browser.close()

    # Duplicate हटाना
    unique = []
    seen = set()

    for item in results:
        key = item["title"] + "|" + item["link"]

        if key not in seen:
            seen.add(key)
            unique.append(item)

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


def load_seen():
    if not os.path.exists(DATA_FILE):
        return set()

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except:
        return set()


def save_seen(seen):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(list(seen), f, ensure_ascii=False)


def main():
    print("🔎 VBU Result checking...")

    seen = load_seen()
    results = get_results()

    print("📋 Results found:", len(results))

    # पहली बार पुराने results को सिर्फ save करेंगे
    # ताकि पुराने results का spam न आए
 if not seen:
            for result in results:
                key = result["title"] + "|" + result["link"]
                seen.add(key)

                message = (
                    "🚨 VBU NEW RESULT 🚨\n\n"
                    f"📢 {result['title']}\n\n"
                    f"🔗 {result['link']}\n\n"
                    "🏫 Vinoba Bhave University"
                )

                send_telegram(message)

            save_seen(seen)
            return

        print("✅ Initial results saved.")
        return

    new_results = []

    for result in results:
        key = result["title"] + "|" + result["link"]

        if key not in seen:
            new_results.append(result)
            seen.add(key)

    for result in new_results:
        message = (
            "🚨 VBU NEW RESULT 🚨\n\n"
            f"📢 {result['title']}\n\n"
            f"🔗 {result['link']}\n\n"
            "🏫 Vinoba Bhave University"
        )

        send_telegram(message)

    save_seen(seen)

    print("✅ Check complete.")


if __name__ == "__main__":
    main()
