#!/usr/bin/env python3
# fetch_content.py v4 - mentions via GraphQL; do_retweet via twikit (tweet_id from n8n)
import os, json, sys, re
import httpx

BEARER = "AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"
QUERY_ID_SEARCH = "-TFXKoMnMTKdEXcCn-eahw"

FEATURES = json.dumps({
    "rweb_tipjar_consumption_enabled": True,
    "responsive_web_graphql_exclude_directive_enabled": True,
    "verified_phone_label_enabled": False,
    "creator_subscriptions_tweet_preview_api_enabled": True,
    "responsive_web_graphql_timeline_navigation_enabled": True,
    "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
    "communities_web_enable_tweet_community_results_fetch": True,
    "c9s_tweet_anatomy_moderator_badge_enabled": True,
    "articles_preview_enabled": True,
    "responsive_web_edit_tweet_api_enabled": True,
    "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
    "view_counts_everywhere_api_enabled": True,
    "longform_notetweets_consumption_enabled": True,
    "tweet_awards_web_tipping_enabled": False,
    "freedom_of_speech_not_reach_fetch_enabled": True,
    "standardized_nudges_misinfo": True,
    "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
    "rweb_video_timestamps_enabled": True,
    "longform_notetweets_rich_text_read_enabled": True,
    "longform_notetweets_inline_media_enabled": True,
    "responsive_web_enhance_cards_enabled": False,
})

def make_headers(ct0):
    return {
        "Authorization": "Bearer " + BEARER,
        "x-csrf-token": ct0,
        "x-twitter-auth-type": "OAuth2Session",
        "x-twitter-active-user": "yes",
        "x-twitter-client-language": "es",
        "Content-Type": "application/json",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
        "Accept": "*/*",
        "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
        "Origin": "https://x.com",
        "Referer": "https://x.com/",
    }

def search(auth_token, ct0, query, count=10):
    cookies = {"auth_token": auth_token, "ct0": ct0}
    variables = json.dumps({"rawQuery": query, "count": count, "product": "Latest", "querySource": ""})
    with httpx.Client(cookies=cookies, timeout=30, follow_redirects=True) as client:
        resp = client.get(
            "https://x.com/i/api/graphql/" + QUERY_ID_SEARCH + "/SearchTimeline",
            params={"variables": variables, "features": FEATURES},
            headers=make_headers(ct0)
        )
    print("HTTP", resp.status_code)
    if resp.status_code != 200:
        print("Error:", resp.text[:300])
        return []
    body = resp.json()
    tweets = []
    try:
        instructions = (body.get("data", {}).get("search_by_raw_query", {})
                        .get("search_timeline", {}).get("timeline", {}).get("instructions", []))
        for instr in instructions:
            if instr.get("type") != "TimelineAddEntries": continue
            for entry in instr.get("entries", []):
                if not entry.get("entryId", "").startswith("tweet-"): continue
                try:
                    result = entry["content"]["itemContent"]["tweet_results"]["result"]
                    legacy = result.get("legacy") or result.get("tweet", {}).get("legacy", {})
                    user_legacy = (result.get("core", {}).get("user_results", {})
                                   .get("result", {}).get("legacy", {}))
                    screen_name = user_legacy.get("screen_name", "unknown")
                    tweet_id = result.get("rest_id") or legacy.get("id_str", "")
                    text = legacy.get("full_text", "")
                    if not tweet_id: continue
                    tweets.append({"tweet_id": tweet_id, "author": screen_name, "text": text,
                                   "url": "https://x.com/" + screen_name + "/status/" + tweet_id})
                except:
                    continue
    except Exception as e:
        print("Parse error:", e)
    return tweets

def do_retweet_twikit(auth_token, ct0, tweet_id):
    """Retweet using twikit from GitHub Actions (no VPS IP block)."""
    try:
        import asyncio
        from twikit import Client

        async def _retweet():
            client = Client('es-ES')
            client.set_cookies({'auth_token': auth_token, 'ct0': ct0})
            await client.retweet(tweet_id)
            return True

        asyncio.run(_retweet())
        print(f"Retweeted tweet {tweet_id}")
        return True
    except Exception as e:
        print(f"Twikit retweet error: {e}")
        return False

def main():
    mode = os.environ.get("FETCH_MODE", "mentions")
    auth_token = os.environ.get("X_AUTH_TOKEN", "")
    ct0 = os.environ.get("X_CT0", "")

    if mode == "mentions":
        query = "@DelphosInnova -from:DelphosInnova -filter:retweets"
        tweets = search(auth_token, ct0, query, 10)
        mentions = [t for t in tweets if t["author"].lower() not in ("delphosinova", "delphosinnovacion", "delphosinova1")]
        print("Mentions found:", len(mentions))
        result = {"mentions": mentions, "count": len(mentions)}
        with open("result.json", "w") as f:
            json.dump(result, f)
        n8n_webhook = os.environ.get("N8N_WEBHOOK", "https://n8n.teamworkz.co/webhook")
        for m in mentions[:3]:
            try:
                with httpx.Client(timeout=15) as client:
                    client.post(n8n_webhook.rstrip("/") + "/f09-mencion", json={
                        "tweet_url": m["url"],
                        "tweet_text": m["text"],
                        "author": m["author"],
                        "tweet_id": m["tweet_id"]
                    })
            except Exception as e:
                print(f"Webhook error: {e}")

    elif mode == "do_retweet":
        tweet_id = os.environ.get("TWEET_ID", "").strip()
        account = os.environ.get("ACCOUNT", "").strip()
        print(f"do_retweet: tweet_id={tweet_id} account={account}")
        if not tweet_id:
            print("ERROR: TWEET_ID not set")
            result = {"retweeted": False, "error": "TWEET_ID not set"}
        elif not auth_token or not ct0:
            print("ERROR: X_AUTH_TOKEN or X_CT0 not set")
            result = {"retweeted": False, "error": "missing auth credentials"}
        else:
            retweeted = do_retweet_twikit(auth_token, ct0, tweet_id)
            result = {"tweet_id": tweet_id, "account": account, "retweeted": retweeted}
        with open("result.json", "w") as f:
            json.dump(result, f)

    # account_tweets mode kept for backward compat but no longer dispatched from n8n
    elif mode == "account_tweets":
        account = os.environ.get("ACCOUNT", "cdti_es").lstrip("@")
        print(f"account_tweets mode for @{account} — this mode is deprecated, use do_retweet instead")
        result = {"tweets": [], "account": account, "count": 0, "note": "deprecated mode"}
        with open("result.json", "w") as f:
            json.dump(result, f)

    else:
        print("Unknown mode:", mode)
        result = {"error": f"unknown mode: {mode}"}
        with open("result.json", "w") as f:
            json.dump(result, f)
        sys.exit(1)

if __name__ == "__main__":
    main()
