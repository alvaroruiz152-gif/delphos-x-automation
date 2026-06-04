#!/usr/bin/env python3
# post_tweet.py - Publica un tweet en X usando cookies de sesion
# Invocado por GitHub Actions via repository_dispatch desde n8n

import os, json, asyncio, random, time, sys
from datetime import datetime
import pytz
import httpx

MADRID_TZ = pytz.timezone("Europe/Madrid")
MAX_DAILY  = 50
BEARER     = "AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"
QUERY_ID   = "SoVnbfCycZ7fERGCwpZkYA"

def get_cookies():
    return {
        "auth_token": os.environ["X_AUTH_TOKEN"],
        "ct0":        os.environ["X_CT0"],
    }

def make_headers(cookies):
    return {
        "Authorization":             f"Bearer {BEARER}",
        "x-csrf-token":              cookies["ct0"],
        "x-twitter-auth-type":       "OAuth2Session",
        "x-twitter-active-user":     "yes",
        "x-twitter-client-language": "es",
        "x-twitter-polling":         "true",
        "Content-Type":              "application/json",
        "User-Agent":                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "Accept":                    "*/*",
        "Accept-Language":           "es-ES,es;q=0.9,en;q=0.8",
        "Origin":                    "https://x.com",
        "Referer":                   "https://x.com/",
        "Sec-Fetch-Dest":            "empty",
        "Sec-Fetch-Mode":            "cors",
        "Sec-Fetch-Site":            "same-origin",
    }

FEATURES = {
    "tweetypie_unmention_optimization_enabled": True,
    "responsive_web_edit_tweet_api_enabled": True,
    "graphql_is_translatable_rweb_tweet_is_translatable_enabled": True,
    "view_counts_everywhere_api_enabled": True,
    "longform_notetweets_consumption_enabled": True,
    "tweet_awards_web_tipping_enabled": False,
    "longform_notetweets_rich_text_read_enabled": True,
    "longform_notetweets_inline_media_enabled": True,
    "rweb_video_timestamps_enabled": True,
    "responsive_web_graphql_exclude_directive_enabled": True,
    "verified_phone_label_enabled": False,
    "freedom_of_speech_not_reach_fetch_enabled": True,
    "standardized_nudges_misinfo": True,
    "tweet_with_visibility_results_prefer_gql_limited_actions_policy_enabled": True,
    "interactive_text_enabled": True,
    "responsive_web_text_conversations_enabled": False,
    "responsive_web_graphql_timeline_navigation_enabled": True,
    "responsive_web_graphql_skip_user_profile_image_extensions_enabled": False,
    "rweb_lists_timeline_redesign_enabled": True,
}

async def post_tweet(text: str, reply_to: str = None):
    cookies = get_cookies()
    variables = {
        "tweet_text": text, "dark_request": False,
        "media": {"media_entities": [], "possibly_sensitive": False},
        "semantic_annotation_ids": [], "disallowed_reply_options": None,
    }
    if reply_to:
        variables["reply"] = {"in_reply_to_tweet_id": reply_to, "exclude_reply_user_ids": []}

    # Anti-ban delay
    delay = random.uniform(2.0, 8.0)
    print(f"Anti-ban delay: {delay:.1f}s")
    time.sleep(delay)

    async with httpx.AsyncClient(cookies=cookies, timeout=20) as client:
        resp = await client.post(
            f"https://x.com/i/api/graphql/{QUERY_ID}/CreateTweet",
            json={"variables": variables, "features": FEATURES, "queryId": QUERY_ID},
            headers=make_headers(cookies)
        )
        body = resp.json()
        if resp.status_code != 200 or "errors" in body:
            raise Exception(f"HTTP {resp.status_code}: {json.dumps(body)[:300]}")
        return body["data"]["create_tweet"]["tweet_results"]["result"]["rest_id"]

async def main():
    # Leer parametros del entorno (pasados por n8n via repository_dispatch)
    text     = os.environ.get("TWEET_TEXT", "")
    reply_to = os.environ.get("REPLY_TO", "") or None
    action   = os.environ.get("ACTION", "tweet")  # tweet | thread | retweet

    if not text and action == "tweet":
        print("ERROR: TWEET_TEXT vacio")
        sys.exit(1)

    # Verificar horario 07:00-22:00 Madrid
    now = datetime.now(MADRID_TZ)
    if not (7 <= now.hour < 22):
        print(f"Fuera de horario ({now.strftime('%H:%M')} Madrid). Tweet ignorado.")
        sys.exit(0)

    if action == "tweet":
        print(f"Publicando tweet ({len(text)} chars): {text[:60]}...")
        tweet_id = await post_tweet(text, reply_to)
        url = f"https://x.com/DelphosInnova/status/{tweet_id}"
        print(f"EXITO: {tweet_id}")
        print(f"URL: {url}")
        # Guardar resultado para n8n
        with open("result.json", "w") as f:
            json.dump({"tweet_id": tweet_id, "url": url, "text": text}, f)

asyncio.run(main())
