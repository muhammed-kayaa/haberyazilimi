import sys
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from playwright.sync_api import sync_playwright
from app.utils.x_parser import extract_tweets_from_timeline_payload, parse_created_at


# ----------------------------
# Helpers
# ----------------------------

def merge_tweets_from_payloads(payloads: list):
    """Birden fazla payload içinden tweetleri çıkarır ve birleştirir (duplicate temizler)."""
    all_tweets = []
    for pld in payloads:
        all_tweets.extend(extract_tweets_from_timeline_payload(pld))

    seen = set()
    uniq = []
    for t in all_tweets:
        tid = t.get("id")
        if tid and tid not in seen:
            uniq.append(t)
            seen.add(tid)

    return uniq


def clean_and_sort_tweets(tweets: list):
    """Mantıksız tarihleri ele ve tweetleri created_at'e göre yeni -> eski sırala."""
    now = datetime.now(timezone.utc)
    cleaned = []

    for t in tweets:
        dt = parse_created_at(t.get("created_at", ""))

        if dt.year < 2007:
            continue
        if dt > now + timedelta(hours=1):
            continue

        cleaned.append((dt, t))

    cleaned.sort(key=lambda x: x[0], reverse=True)
    return [t for _, t in cleaned]


def top_liked_last_24h_strict(username: str, tweets: list, top_n: int = 3):
    """Sadece son 24 saat içindeki tweetlerden Top N Like verir."""
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(hours=24)

    last24 = []
    for t in tweets:
        created = parse_created_at(t.get("created_at", ""))
        if created >= cutoff:
            last24.append(t)

    last24.sort(key=lambda x: x.get("like_count", 0), reverse=True)

    top = last24[:top_n]
    links = [f"https://x.com/{username}/status/{t['id']}" for t in top]

    return links, top


# ----------------------------
# Main Fetch (PROFILE)
# ----------------------------

def fetch_user_profile_payloads(username: str, headless: bool = True, timeout_ms: int = 45000):
    """
    Profil sayfasını açar:
      https://x.com/USERNAME

    ✅ Parser ile tam uyumlu (en stabil yöntem).
    ✅ cookies_playwright.json yükleyerek loginli modda çalışır.
    """
    timeline_payloads = []

    PROJECT_ROOT = Path(__file__).resolve().parents[2]
    out_dir = PROJECT_ROOT / "crawler" / "data"
    out_dir.mkdir(exist_ok=True)

    cookies_path = out_dir / "cookies_playwright.json"

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context()

        # ✅ cookie yükle
        if cookies_path.exists():
            cookies = json.load(open(cookies_path, "r", encoding="utf-8"))
            context.add_cookies(cookies)
            print("[INFO] cookies_playwright.json yüklendi (loginli mod).")
        else:
            print("[WARN] cookies_playwright.json bulunamadı. Guest modda devam edilecek.")

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
        page.wait_for_timeout(5000)

        # scroll ile yeni istek tetikle
        for i in range(25):
            page.mouse.wheel(0, 2500)
            page.wait_for_timeout(2000)
            print(f"[INFO] Scroll {i+1}/25 yapıldı...")

        context.close()
        browser.close()

    if not timeline_payloads:
        raise RuntimeError(f"{username} için timeline JSON yakalanamadı. X kısıtlıyor olabilir.")

    return timeline_payloads


# ----------------------------
# Program
# ----------------------------

def main():
    if len(sys.argv) < 3:
        print("Kullanım: python app/scripts/fetch_top3.py <username1> <username2>")
        sys.exit(1)

    usernames = sys.argv[1:3]

    PROJECT_ROOT = Path(__file__).resolve().parents[2]
    out_dir = PROJECT_ROOT / "crawler" / "data"
    out_dir.mkdir(exist_ok=True)

    for username in usernames:
        try:
            payloads = fetch_user_profile_payloads(username, headless=True)

            tweets = merge_tweets_from_payloads(payloads)
            tweets = clean_and_sort_tweets(tweets)

            # Debug kayıtlar
            with open(out_dir / f"{username}_raw.json", "w", encoding="utf-8") as f:
                json.dump(payloads, f, ensure_ascii=False, indent=2)

            with open(out_dir / f"{username}_tweets.json", "w", encoding="utf-8") as f:
                json.dump(tweets, f, ensure_ascii=False, indent=2)

            links, top_tweets = top_liked_last_24h_strict(username, tweets, top_n=3)

            print(f"\n=== @{username} | Son 24 saatte Top 3 (Like) ===")
            if not links:
                print("❌ Son 24 saatte tweet bulunamadı.")
            else:
                for i, link in enumerate(links, 1):
                    print(f"{i}. {link}  (❤️ {top_tweets[i-1]['like_count']})")

        except Exception as e:
            print(f"\n[ERROR] @{username}: {e}")

    print("\n[OK] Bitti.")


if __name__ == "__main__":
    main()