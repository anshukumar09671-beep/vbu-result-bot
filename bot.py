import os
import json
import time
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# =========================
# VBU SETTINGS
# =========================

VBU_URL = "https://www.vbu.ac.in/"
BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

DATA_FILE = "seen.json"


# =========================
# VBU RESULT CHECK
# =========================

def get_results():

    response = requests.get(
        VBU_URL,
        timeout=30,
        headers={
            "User-Agent": "Mozilla/5.0"
        }
    )

    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    results = []

    for a in soup.find_all("a", href=True):

        title = a.get_text(" ", strip=True)

        if not title:
            continue

        if "result" not in title.lower():
            continue

        link = urljoin(VBU_URL, a["href"])

        results.append({
            "title": title,
            "link": link
        })

    # Duplicate हटाना
    unique_results = []
    already_found = set()

    for result in results:

        key = result["title"] + "|" + result["link"]

        if key not in already_found:

            already_found.add(key)
            unique_results.append(result)

    return unique_results


# =========================
# TELEGRAM MESSAGE
# =========================

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


# =========================
# LOAD OLD RESULTS
# =========================

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


# =========================
# SAVE RESULTS
# =========================

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


# =========================
# MAIN
# =========================

def main():

    print("🔎 VBU Result checking...")

    seen = load_seen()

    results = get_results()

    print("📄 Results found:", len(results))


    # पहली बार पुराने results को सिर्फ save करेंगे
    # ताकि पुराने result का spam न आए

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


    # =========================
    # NEW RESULT FIND
    # =========================

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


    # =========================
    # SEND TELEGRAM
    # =========================

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


# =========================
# START
# =========================

if __name__ == "__main__":
    main()
