#!/usr/bin/env python3
# fetch_content.py v3 - mentions via GraphQL, account_tweets via Nitter RSS + twikit retweet
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

# Nitter instances to try in order (fallback mechanism)
NITTER_INSTANCES = [
    "https://nitter.poast.org",
    "https://nitter.privacydev.net",
    "https://nitter.net",
    "https://xcancel.com",
]

def fetch_rss_tweets(account, max_items=5):
    """Fetch latest tweets from account via Nitter RSS, trying multiple instances."""
    for instance in NITTER_INSTANCES:
        rss_url = f"{instance}/{account}/rss"
        print(f"Trying RSS: {rss_url}")
        try:
            with httpx.Client(timeout=15, follow_redirects=True,
                              headers={"User-Agent": "FeedFetcher-Google; (+http://www.google.com/feedfetcher.html)",
                                       "Accept": "application/rss+xml, application/xml, */*"}) as client:
                resp = client.get(rss_url)
            print(f"  HTTP {resp.status_code}, len={len(resp.text)}")
            xml = resp.text
            # Accept 200 or 403 (some Nitter instances return 403 but still serve RSS)
            # Reject if explicitly blocked or has no items
            if resp.status_code not in (200, 403):
                continue
            if "not yet whitelisted" in xml or "<item>" not in xml:
                print("  Blocked or empty feed, trying next instance")
                continue
        except Exception as e:
            print(f"  Error: {e}")
            continue

        tweets = []
        pos = 0
        while len(tweets) < max_items:
            item_pos = xml.find('<item>', pos)
            if item_pos == -1:
                break
            item_end = xml.find('</item>', item_pos)
            if item_end == -1:
                break
            item = xml[item_pos:item_end + 7]

            # link / guid → tweet URL
            link = ""
            ls = item.find('<link>') + 6
            le = item.find('</link>')
            if ls > 5 and le > ls:
                link = item[ls:le].strip()
            if not link:
                gs = item.find('<guid>') + 6
                ge = item.find('</guid>')
                if gs > 5 and ge > gs:
                    link = item[gs:ge].strip()

            # Normalize to x.com URL
            link = re.sub(r'https?://[^/]+/', 'https://x.com/', link)

            # title → tweet text
            ts = item.find('<title>') + 7
            te = item.find('</title>')
            text = ""
            if ts > 6 and te > ts:
                text = item[ts:te].replace('<![CDATA[', '').replace(']]>', '').strip()
                text = re.sub(r'<[^>]+>', '', text).strip()

            # Extract tweet_id
            try:
                parts = link.rstrip('/').split('/')
                si = parts.index('status')
                tweet_id = parts[si + 1].split('?')[0]
                if tweet_id and text:
                    tweets.append({
                        "tweet_id": tweet_id,
                        "author": account,
                        "text": text,
                        "url": f"https://x.com/{account}/status/{tweet_id}"
                    })
            except (ValueError, IndexError):
                pass
            pos = item_end + 7

        if tweets:
            print(f"  ✅ Got {len(tweets)} tweets from {instance}")
            return tweets

    print("No tweets found from any Nitter instance")
    return []

def do_retweet_twikit(auth_token, ct0, tweet_id):
    """Retweet from GitHub Actions using twikit (bypasses VPS IP block)."""
    try:
        import asyncio
        from twikit import Client

        async def _retweet():
            client = Client('es-ES')
            client.set_cookies({'auth_token': auth_token, 'ct0': ct0})
            await client.retweet(tweet_id)
            return True

        asyncio.run(_retweet())
        print(f"✅ Retweeted tweet {tweet_id}")
        return True
    except Exception as e:
        print(f"Twikit retweet error: {e}")
        return False

def post_to_webhook(n8n_webhook, path, payload):
    url = n8n_webhook.rstrip("/") + "/" + path
    try:
        with httpx.Client(timeout=15) as client:
            r = client.post(url, json=payload)
            print(f"Webhook {path}: HTTP {r.status_code}")
            return r.status_code
    except Exception as e:
        print(f"Webhook error: {e}")
        return 0

def main():
    mode = os.environ.get("FETCH_MODE", "mentions")
    auth_token = os.environ.get("X_AUTH_TOKEN", "")
    ct0 = os.environ.get("X_CT0", "")
    n8n_webhook = os.environ.get("N8N_WEBHOOK", "https://n8n.teamworkz.co/webhook")

    if mode == "mentions":
        query = "@DelphosInnova -from:DelphosInnova -filter:retweets"
        tweets = search(auth_token, ct0, query, 10)
        mentions = [t for t in tweets if t["author"].lower() not in ("delphosinova", "delphosinnovacion", "delphosinova1")]
        print("Mentions found:", len(mentions))
        result = {"mentions": mentions, "count": len(mentions)}
        with open("result.json", "w") as f:
            json.dump(result, f)
        for m in mentions[:3]:
            post_to_webhook(n8n_webhook, "f09-mencion", {
                "tweet_url": m["url"],
                "tweet_text": m["text"],
                "author": m["author"],
                "tweet_id": m["tweet_id"]
            })

    elif mode == "account_tweets":
        account = os.environ.get("ACCOUNT", "cdti_es").lstrip("@")
        tweets = fetch_rss_tweets(account, max_items=5)
        print(f"Tweets from @{account}: {len(tweets)}")

        retweeted = False
        if tweets and auth_token and ct0:
            # Retweet from GitHub Actions — no VPS IP block issue
            retweeted = do_retweet_twikit(auth_token, ct0, tweets[0]["tweet_id"])

        result = {"tweets": tweets, "account": account, "count": len(tweets), "retweeted": retweeted}
        with open("result.json", "w") as f:
            json.dump(result, f)

        # Notify n8n (for Telegram confirmation)
        if tweets:
            t = tweets[0]
            post_to_webhook(n8n_webhook, "f09-retweet", {
                "tweet_id": t["tweet_id"],
                "tweet_url": t["url"],
                "author": t["author"],
                "text": t["text"],
                "retweeted": retweeted
            })
        else:
            print("No tweets to retweet")

    else:
        print("Unknown mode:", mode)
        sys.exit(1)

if __name__ == "__main__":
    main()
