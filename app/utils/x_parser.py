from __future__ import annotations
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

def _get(d: dict, path: list, default=None):
    cur = d
    for p in path:
        if cur is None:
            return default
        if isinstance(p, int):
            if isinstance(cur, list) and len(cur) > p:
                cur = cur[p]
            else:
                return default
        else:
            if isinstance(cur, dict):
                cur = cur.get(p)
            else:
                return default
    return cur if cur is not None else default

def parse_created_at(value: str) -> datetime:
    if not value:
        return datetime.fromtimestamp(0, tz=timezone.utc)

    try:
        return datetime.strptime(value, "%a %b %d %H:%M:%S %z %Y")
    except Exception:
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except Exception:
            return datetime.fromtimestamp(0, tz=timezone.utc)

def normalize_tweet(tweet: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    tid = tweet.get("id_str") or tweet.get("rest_id") or tweet.get("id")
    if not tid:
        return None

    created_at = tweet.get("created_at") or _get(tweet, ["legacy", "created_at"])
    legacy = tweet.get("legacy", tweet)

    like_count = legacy.get("favorite_count") or legacy.get("like_count") or 0
    text = legacy.get("full_text") or legacy.get("text") or ""

    return {
        "id": str(tid),
        "created_at": created_at,
        "like_count": int(like_count),
        "text": text,
    }

def extract_tweets_from_timeline_payload(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    tweets: List[Dict[str, Any]] = []

    instructions = _get(payload, ["data", "user", "result", "timeline_v2", "timeline", "instructions"], [])
    if not instructions:
        instructions = _get(payload, ["data", "user", "result", "timeline", "timeline", "instructions"], [])

    for inst in instructions or []:
        entries = inst.get("entries") or []
        for e in entries:
            content = e.get("content") or {}
            item = content.get("itemContent") or {}
            tweet_result = _get(item, ["tweet_results", "result"])

            if isinstance(tweet_result, dict):
                t = normalize_tweet(tweet_result)
                if t:
                    tweets.append(t)

    if not tweets:
        global_tweets = _get(payload, ["globalObjects", "tweets"], {})
        if isinstance(global_tweets, dict):
            for tid, t in global_tweets.items():
                t["id"] = tid
                nt = normalize_tweet(t)
                if nt:
                    tweets.append(nt)

    seen = set()
    uniq = []
    for t in tweets:
        if t["id"] not in seen:
            uniq.append(t)
            seen.add(t["id"])
    return uniq
