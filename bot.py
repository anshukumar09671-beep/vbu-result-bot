import os
import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

VBU_URL = "https://www.vbu.ac.in/notice/result"

BOT_TOKEN = os.environ["BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]

DATA_FILE = "seen.json"


def get_results():
    response = requests.get(
        VBU_URL,
        timeout=30,
        headers={"User-Agent": "Mozilla/5.0"}
    )

    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")

    results = []

    for a in soup.find_all("a", href=True):
        title = a.get_text(" ", strip=True)
        link = urljoin(VBU_URL, a["href"])

        if "result" in title.lower():
            results.append({
                "title": title,
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
        return None

    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except:
        return set()


def save_seen(seen):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(list(seen), f, ensure_ascii=False)


def main():
    results = get_results()

    current = set()

    for result in results:
        key = result["title"] + "|" + result["link"]
        current.add(key)

    seen = load_seen()

    # पहली बार: पुराने results को सिर्फ याद रखो
    if seen is None:
        save_seen(current)
        return

    new_results = []

    for result in results:
        key = result["title"] + "|" + result["link"]

        if key not in seen:
            new_results.append(result)

    for result in reversed(new_results):
        message = (
            "🚨 VBU NEW RESULT 🚨\n\n"
            f"📢 {result['title']}\n\n"
            f"🔗 {result['link']}\n\n"
            "🏫 Vinoba Bhave University"
        )

        send_telegram(message)

    save_seen(seen | current)


if __name__ == "__main__":
    main()
