import sys
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright
from app.utils.x_parser import extract_tweets_from_timeline_payload, parse_created_at


def fetch_user_timeline_json(username: str, headless: bool = True, timeout_ms: int = 45000):
    timeline_payloads = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context()
        page = context.new_page()

        def handle_response(response):
            url = response.url
            if ("UserTweets" in url) or ("UserTweetsAndReplies" in url) or ("UserMedia" in url) or ("graphql" in url):
                try:
                    data = response.json()
                    txt = json.dumps(data)
                    if "timeline" in txt and "instructions" in txt:
                        timeline_payloads.append(data)
                except:
                    pass

        page.on("response", handle_response)

        url = f"https://x.com/{username}"
        print(f"[INFO] Açılıyor: {url}")
        page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)

        # timeline requestleri için bekle
        page.wait_for_timeout(12000)

        browser.close()

    if not timeline_payloads:
        raise RuntimeError(f"{username} için timeline JSON yakalanamadı. Captcha veya login gerekebilir.")

    return timeline_payloads[-1]


def top_liked_last_24h(username: str, tweets: list, top_n: int = 3):
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=24)

    filtered = []
    for t in tweets:
        created = parse_created_at(t.get("created_at", ""))
        if created >= cutoff:
            filtered.append(t)

    filtered.sort(key=lambda x: x.get("like_count", 0), reverse=True)

    links = []
    top = filtered[:top_n]
    for t in top:
        tid = t["id"]
        links.append(f"https://x.com/{username}/status/{tid}")

    return links, top


def main():
    if len(sys.argv) < 3:
        print("Kullanım: python app/scripts/fetch_top3.py <username1> <username2>")
        sys.exit(1)

    usernames = sys.argv[1:3]
    out_dir = Path("data")
    out_dir.mkdir(exist_ok=True)

    for username in usernames:
        try:
            payload = fetch_user_timeline_json(username, headless=True)
            tweets = extract_tweets_from_timeline_payload(payload)

            with open(out_dir / f"{username}_raw.json", "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)

            with open(out_dir / f"{username}_tweets.json", "w", encoding="utf-8") as f:
                json.dump(tweets, f, ensure_ascii=False, indent=2)

            links, top_tweets = top_liked_last_24h(username, tweets, top_n=3)

            print(f"\n=== @{username} | Son 24 saatte Top 3 (Like) ===")
            if not links:
                print("Son 24 saatte tweet bulunamadı (veya timeline boş).")
            else:
                for i, link in enumerate(links, 1):
                    print(f"{i}. {link}  (❤️ {top_tweets[i-1]['like_count']})")

        except Exception as e:
            print(f"\n[ERROR] @{username}: {e}")
            print("Çözüm: Captcha çıktıysa cookie ile login moduna geçebiliriz.")

    print("\n[OK] Bitti.")


if __name__ == "__main__":
    main()
