import os
import json
import time
import requests
from bs4 import BeautifulSoup

VBU_URL = "https://www.vbu.ac.in/notice/result"
BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

DATA_FILE = "seen.json"


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
        text = a.get_text(" ", strip=True)

        if "Result" in text or "RESULT" in text:
            link = a["href"]

            if link.startswith("/"):
                link = "https://www.vbu.ac.in" + link
            elif not link.startswith("http"):
                link = "https://www.vbu.ac.in/" + link

            results.append({
                "title": text,
                "link": link
            })

    return results


def send_telegram(message):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"

    requests.post(
        url,
        data={
            "chat_id": CHAT_ID,
            "text": message,
            "disable_web_page_preview": False
        },
        timeout=30
    )


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
    seen = load_seen()
    results = get_results()

    new_results = []

    for result in results:
        key = result["title"] + "|" + result["link"]

        if key not in seen:
            new_results.append(result)
            seen.add(key)

    for result in reversed(new_results):
        message = (
            "🚨 VBU NEW RESULT 🚨\n\n"
            f"📢 {result['title']}\n\n"
            f"🔗 {result['link']}\n\n"
            "🏫 Vinoba Bhave University"
        )

        send_telegram(message)

    save_seen(seen)


if __name__ == "__main__":
    main()
