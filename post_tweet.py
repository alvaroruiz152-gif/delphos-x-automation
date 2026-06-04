#!/usr/bin/env python3
# post_tweet.py - Publica en X via Playwright (navegador real)
# GitHub Actions: IP Microsoft Azure + Chrome real = sin detección de bot

import os, json, asyncio, random, time, sys
from datetime import datetime
import pytz

MADRID_TZ = pytz.timezone("Europe/Madrid")

def check_hours():
    now = datetime.now(MADRID_TZ)
    return 7 <= now.hour < 22

def anti_ban_delay():
    delay = random.uniform(3.0, 9.0)
    print(f"Delay: {delay:.1f}s")
    time.sleep(delay)

async def post_via_playwright(text: str, reply_to: str = None):
    from playwright.async_api import async_playwright

    auth_token = os.environ["X_AUTH_TOKEN"]
    ct0        = os.environ["X_CT0"]

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=["--no-sandbox","--disable-dev-shm-usage",
                  "--disable-blink-features=AutomationControlled"]
        )
        ctx = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            locale="es-ES",
            viewport={"width":1280,"height":800},
        )
        # Ocultar que es headless
        await ctx.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")

        # Cargar cookies de sesión (no necesita login)
        await ctx.add_cookies([
            {"name":"auth_token","value":auth_token,"domain":".x.com","path":"/","secure":True,"httpOnly":True,"sameSite":"None"},
            {"name":"ct0","value":ct0,"domain":".x.com","path":"/","secure":True,"sameSite":"Lax"},
        ])

        page = await ctx.new_page()
        page.set_default_timeout(30000)

        # Abrir X
        print("Abriendo x.com...")
        await page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(3)

        # Verificar que estamos logueados
        url = page.url
        print(f"URL: {url}")
        if "login" in url or "i/flow" in url:
            raise Exception("Sesión expirada — actualiza las cookies")

        # Si es reply, ir al tweet primero
        if reply_to:
            print(f"Abriendo tweet {reply_to} para responder...")
            await page.goto(f"https://x.com/i/web/status/{reply_to}", wait_until="domcontentloaded")
            await asyncio.sleep(2)
            # Click en responder
            reply_btn = page.locator('[data-testid="reply"]').first
            await reply_btn.click()
            await asyncio.sleep(1)
        else:
            # Click en el botón de redactar
            compose_btn = page.locator('[data-testid="SideNav_NewTweet_Button"]').first
            if await compose_btn.count() > 0:
                await compose_btn.click()
                await asyncio.sleep(1)

        # Escribir el tweet en el editor
        print(f"Escribiendo tweet: {text[:60]}...")
        editor = page.locator('[data-testid="tweetTextarea_0"]').first
        await editor.wait_for(state="visible", timeout=10000)
        await editor.click()
        await asyncio.sleep(0.5)

        # Escribir carácter a carácter para simular humano
        await page.keyboard.type(text, delay=random.randint(20, 60))
        await asyncio.sleep(1)

        # Verificar longitud
        char_count = await page.evaluate("""
            () => {
                const el = document.querySelector('[data-testid="tweetTextarea_0"]');
                return el ? el.textContent.length : 0;
            }
        """)
        print(f"Caracteres escritos: {char_count}")

        # Pulsar el botón de publicar
        submit_btn = page.locator('[data-testid="tweetButtonInline"]').first
        if await submit_btn.count() == 0:
            submit_btn = page.locator('[data-testid="tweetButton"]').first
        await submit_btn.wait_for(state="visible", timeout=5000)
        await asyncio.sleep(0.5)
        await submit_btn.click()
        print("Tweet enviado, esperando confirmación...")
        await asyncio.sleep(4)

        # Obtener el ID del tweet publicado buscando en la timeline
        tweet_id = None
        try:
            # Intentar obtener el ID del último tweet publicado
            result = await page.evaluate("""
                () => {
                    const links = Array.from(document.querySelectorAll('a[href*="/status/"]'));
                    for (const link of links) {
                        const m = link.href.match(/status\\/([0-9]+)/);
                        if (m) return m[1];
                    }
                    return null;
                }
            """)
            tweet_id = result
        except:
            pass

        await browser.close()
        return tweet_id or "published"

async def main():
    text     = os.environ.get("TWEET_TEXT", "")
    reply_to = os.environ.get("REPLY_TO", "") or None
    action   = os.environ.get("ACTION", "tweet")

    if not text:
        print("ERROR: TWEET_TEXT vacío"); sys.exit(1)

    if len(text) > 280:
        text = text[:277] + "..."

    # Verificar horario
    if not check_hours():
        now = datetime.now(MADRID_TZ).strftime("%H:%M")
        print(f"Fuera de horario ({now} Madrid, permitido 07:00-22:00). Tweet ignorado.")
        with open("result.json","w") as f:
            json.dump({"status":"deferred","reason":f"fuera de horario ({now})"}, f)
        sys.exit(0)

    print(f"Publicando: {text[:70]}...")
    anti_ban_delay()

    tweet_id = await post_via_playwright(text, reply_to)
    url = f"https://x.com/DelphosInnova/status/{tweet_id}" if tweet_id != "published" else "https://x.com/DelphosInnova"
    print(f"EXITO: {tweet_id}")
    print(f"URL: {url}")
    with open("result.json","w") as f:
        json.dump({"tweet_id":tweet_id,"url":url,"text":text}, f)

asyncio.run(main())
