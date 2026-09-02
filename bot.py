import os
import json
from urllib.parse import urljoin
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

        print("🌐 VBU Result page opening...")

        page.goto(
            VBU_URL,
            wait_until="networkidle",
            timeout=60000
        )

        page.wait_for_timeout(5000)

        # सभी links पढ़ना
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

                # सिर्फ Result वाले links
                if "result" not in title.lower():
                    continue

                link = urljoin(VBU_URL, href)

                results.append({
                    "title": title,
                    "link": link
                })

            except Exception:
                continue

        browser.close()

    # Duplicate हटाना
    unique = []
    seen_keys = set()

    for result in results:

        key = result["title"] + "|" + result["link"]

        if key not in seen_keys:

            seen_keys.add(key)
            unique.append(result)

    return unique


def send_telegram(message):

    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    response = __import__("requests").post(
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

        with open(
            DATA_FILE,
            "r",
            encoding="utf-8"
        ) as f:

            return set(json.load(f))

    except Exception:

        return set()


def save_seen(seen):

    with open(
        DATA_FILE,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            list(seen),
            f,
            ensure_ascii=False,
            indent=2
        )


def main():

    print("🔎 VBU Result checking...")

    seen = load_seen()

    results = get_results()

    print("📄 Results found:", len(results))

    # पहली बार पुराने results save
    if not seen:

        for result in results:

            key = (
                result["title"]
                + "|"
                + result["link"]
            )

            seen.add(key)

        save_seen(seen)

        print("✅ Initial results saved.")

        return

    # नए results
    new_results = []

    for result in results:

        key = (
            result["title"]
            + "|"
            + result["link"]
        )

        if key not in seen:

            new_results.append(result)
            seen.add(key)

    print("🆕 New results:", len(new_results))

    # Telegram भेजना
    for result in new_results:

        message = (
            "🚨 VBU NEW RESULT 🚨\n\n"
            f"📢 {result['title']}\n\n"
            f"🔗 {result['link']}\n\n"
            "🏫 Vinoba Bhave University"
        )

        send_telegram(message)

        print("✅ Telegram sent.")

    save_seen(seen)

    print("✅ Check complete.")


if __name__ == "__main__":
    main()
