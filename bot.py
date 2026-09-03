import os
import json
import requests
from urllib.parse import urljoin
from playwright.sync_api import sync_playwright

VBU_RESULT_URL = "https://www.vbu.ac.in/notice/result"
VBU_NOTICE_URL = "https://www.vbu.ac.in/notice"

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

DATA_FILE = "seen.json"


def get_vbu_items(url, item_type):
    items = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        print("🌐 Opening:", url)

        page.goto(
            url,
            wait_until="domcontentloaded",
            timeout=60000
        )

        page.wait_for_timeout(5000)

        links = page.locator("a[href]")
        count = links.count()

        print("🔗 Links found:", count)

        for i in range(count):
            try:
                a = links.nth(i)

                title = a.inner_text().strip()
                href = a.get_attribute("href")

                if not title or not href:
                    continue

                link = urljoin(url, href)

                text = title.lower()

                # Result page
                if item_type == "result":
                    if "result" in text:
                        items.append({
                            "type": "result",
                            "title": title,
                            "link": link
                        })

                # Notice page
                elif item_type == "notice":
                    if title:
                        items.append({
                            "type": "notice",
                            "title": title,
                            "link": link
                        })

            except Exception:
                continue

        browser.close()

    # Duplicate हटाना
    unique = []
    found = set()

    for item in items:
        key = item["type"] + "|" + item["title"] + "|" + item["link"]

        if key not in found:
            found.add(key)
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
            ensure_ascii=False,
            indent=2
        )


def main():

    print("🚀 VBU Result + Notice Bot Started")

    seen = load_seen()

    # =========================
    # RESULT CHECK
    # =========================

    results = get_vbu_items(
        VBU_RESULT_URL,
        "result"
    )

    print("📄 Results found:", len(results))


    # =========================
    # NOTICE CHECK
    # =========================

    notices = get_vbu_items(
        VBU_NOTICE_URL,
        "notice"
    )

    print("📢 Notices found:", len(notices))


    all_items = results + notices


    # =========================
    # FIRST RUN
    # =========================

    if not seen:

        for item in all_items:

            key = (
                item["type"]
                + "|"
                + item["title"]
                + "|"
                + item["link"]
            )

            seen.add(key)

        save_seen(seen)

        print("✅ Existing items saved.")
        return


    # =========================
    # NEW ITEMS
    # =========================

    new_items = []

    for item in all_items:

        key = (
            item["type"]
            + "|"
            + item["title"]
            + "|"
            + item["link"]
        )

        if key not in seen:

            new_items.append(item)
            seen.add(key)


    print("🆕 New items:", len(new_items))


    # =========================
    # SEND TELEGRAM
    # =========================

    for item in new_items:

        if item["type"] == "result":

            message = (
                "🚨 VBU NEW RESULT 🚨\n\n"
                f"📢 {item['title']}\n\n"
                f"🔗 {item['link']}\n\n"
                "🏫 Vinoba Bhave University"
            )

        else:

            message = (
                "🔔 VBU NEW NOTICE 🔔\n\n"
                f"📢 {item['title']}\n\n"
                f"🔗 {item['link']}\n\n"
                "🏫 Vinoba Bhave University"
            )

        send_telegram(message)

        print("✅ Telegram sent:", item["title"])


    save_seen(seen)

    print("✅ Check complete.")


if __name__ == "__main__":
    main()
