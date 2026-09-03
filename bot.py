import os
import json
import re
import requests
from urllib.parse import urljoin
from playwright.sync_api import sync_playwright

VBU_RESULT_URL = "https://www.vbu.ac.in/notice/result"
VBU_NOTICE_URL = "https://www.vbu.ac.in/notice"

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

DATA_FILE = "seen.json"


# =========================================
# CHECK VALID LINK
# =========================================

def valid_link(title, href):

    if not title or not href:
        return False

    title = " ".join(title.split()).strip()
    href = href.strip()

    low_title = title.lower()
    low_href = href.lower()

    # बेकार / dynamic links
    bad = [
        "javascript:",
        "void(0)",
        "{{",
        "}}",
        "pageno",
        "?page=",
        "&page=",
        "#",
        "/login",
        "/register"
    ]

    for x in bad:
        if x in low_title or x in low_href:
            return False

    # बहुत छोटे titles जैसे "of", "next", "prev"
    if len(title) < 8:
        return False

    navigation = [
        "next",
        "previous",
        "prev",
        "first",
        "last",
        "home",
        "login",
        "register",
        "search",
        "menu"
    ]

    if low_title in navigation:
        return False

    return True


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

        print("🔗 Total links:", count)

        for i in range(count):

            try:

                a = links.nth(i)

                title = a.inner_text().strip()
                href = a.get_attribute("href")

                title = " ".join(title.split())

                if not valid_link(title, href):
                    continue

                link = urljoin(url, href)

                title_lower = title.lower()
                link_lower = link.lower()


                # =====================================
                # RESULT
                # =====================================

                if item_type == "result":

                    # Result page पर केवल actual result entries
                    if "result" not in title_lower:
                        continue

                    # navigation/template हटाना
                    if (
                        "page" in title_lower
                        or "next" in title_lower
                        or "prev" in title_lower
                        or "previous" in title_lower
                    ):
                        continue

                    items.append({
                        "type": "result",
                        "title": title,
                        "link": link
                    })


                # =====================================
                # NOTICE
                # =====================================

                elif item_type == "notice":

                    # सिर्फ वास्तविक notice/document links
                    is_notice = (
                        "notice" in title_lower
                        or "notification" in title_lower
                        or "circular" in title_lower
                        or "publication" in link_lower
                        or ".pdf" in link_lower
                    )

                    if not is_notice:
                        continue

                    # Dynamic/template entries फिर से block
                    if any(x in title_lower for x in [
                        "{{",
                        "pageno",
                        "page",
                        "javascript",
                        "void"
                    ]):
                        continue

                    items.append({
                        "type": "notice",
                        "title": title,
                        "link": link
                    })

            except Exception as e:

                print("⚠️ Skip:", e)
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
# SEEN DATA
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

    print("🚀 VBU Bot Started")


    seen = load_seen()


    # =========================================
    # RESULT
    # =========================================

    results = get_vbu_items(
        VBU_RESULT_URL,
        "result"
    )

    print(
        "📄 Valid Results:",
        len(results)
    )


    # =========================================
    # NOTICE
    # =========================================

    notices = get_vbu_items(
        VBU_NOTICE_URL,
        "notice"
    )

    print(
        "📢 Valid Notices:",
        len(notices)
    )


    all_items = results + notices


    # =========================================
    # FIRST RUN
    # =========================================

    if not seen:

        print("🟢 First run")

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
            "🚫 No Telegram message sent."
        )

        return


    # =========================================
    # FIND NEW
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
        "🆕 NEW ITEMS:",
        len(new_items)
    )


    # =========================================
    # SEND
    # =========================================

    for item in new_items:

        if item["type"] == "result":

            message = (
                "🚨 VBU NEW RESULT 🚨\n\n"
                f"📢 {item['title']}\n\n"
                f"🔗 {item['link']}\n\n"
                "🏫 Vinoba Bhave University, Hazaribag"
            )

        else:

            message = (
                "🔔 VBU NEW NOTICE 🔔\n\n"
                f"📢 {item['title']}\n\n"
                f"🔗 {item['link']}\n\n"
                "🏫 Vinoba Bhave University, Hazaribag"
            )


        send_telegram(message)

        print(
            "✅ Sent:",
            item["title"]
        )


    save_seen(seen)

    print("✅ Check complete.")


# =========================================
# START
# =========================================

if __name__ == "__main__":
    main()
