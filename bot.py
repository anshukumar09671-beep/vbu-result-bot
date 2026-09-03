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


# =========================================
# GET VBU ITEMS
# =========================================

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

                title_clean = " ".join(title.split())

                href_clean = href.strip()

                # =====================================
                # INVALID / DYNAMIC LINKS
                # =====================================

                invalid_words = [
                    "{{",
                    "}}",
                    "javascript:",
                    "void(0)",
                    "pageno",
                    "?page=",
                    "&page=",
                    "login",
                    "register",
                    "#"
                ]

                combined = (
                    title_clean.lower()
                    + " "
                    + href_clean.lower()
                )

                if any(word in combined for word in invalid_words):
                    continue


                link = urljoin(url, href_clean)


                # =====================================
                # RESULT
                # =====================================

                if item_type == "result":

                    text = title_clean.lower()

                    if (
                        "result" in text
                        or "results" in text
                    ):

                        items.append({
                            "type": "result",
                            "title": title_clean,
                            "link": link
                        })


                # =====================================
                # NOTICE
                # =====================================

                elif item_type == "notice":

                    title_lower = title_clean.lower()
                    link_lower = link.lower()

                    # केवल ऐसे links जिनमें notice/publication
                    # अथवा document/pdf जैसा संकेत हो

                    if (
                        "notice" in title_lower
                        or "notification" in title_lower
                        or "notice" in link_lower
                        or "publication" in link_lower
                        or ".pdf" in link_lower
                    ):

                        items.append({
                            "type": "notice",
                            "title": title_clean,
                            "link": link
                        })


            except Exception as e:

                print("⚠️ Link error:", e)

                continue


        browser.close()


    # =========================================
    # REMOVE DUPLICATES
    # =========================================

    unique = []

    found = set()

    for item in items:

        key = (
            item["type"]
            + "|"
            + item["title"]
            + "|"
            + item["link"]
        )

        if key not in found:

            found.add(key)

            unique.append(item)


    return unique


# =========================================
# TELEGRAM
# =========================================

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


# =========================================
# LOAD SEEN
# =========================================

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


# =========================================
# SAVE SEEN
# =========================================

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


# =========================================
# MAIN
# =========================================

def main():

    print("🚀 VBU Result + Notice Bot Started")


    seen = load_seen()


    # =========================================
    # RESULT CHECK
    # =========================================

    results = get_vbu_items(
        VBU_RESULT_URL,
        "result"
    )

    print(
        "📄 Valid Results found:",
        len(results)
    )


    # =========================================
    # NOTICE CHECK
    # =========================================

    notices = get_vbu_items(
        VBU_NOTICE_URL,
        "notice"
    )

    print(
        "📢 Valid Notices found:",
        len(notices)
    )


    all_items = results + notices


    # =========================================
    # FIRST RUN
    # =========================================

    if not seen:

        print(
            "🟢 First run detected."
        )

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

        print(
            "✅ Existing items saved."
        )

        print(
            "ℹ️ No Telegram message sent."
        )

        return


    # =========================================
    # FIND NEW ITEMS
    # =========================================

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


    print(
        "🆕 New items:",
        len(new_items)
    )


    # =========================================
    # SEND NEW ITEMS
    # =========================================

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


        print(
            "✅ Telegram sent:",
            item["title"]
        )


    save_seen(seen)


    print(
        "✅ Check complete."
    )


# =========================================
# START
# =========================================

if __name__ == "__main__":

    main()
