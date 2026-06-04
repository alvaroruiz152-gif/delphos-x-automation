#!/usr/bin/env python3
# post_tweet.py - Publica en X via Playwright (Chrome real, sin deteccion bot)

import os, json, asyncio, random, time, sys
from datetime import datetime
import pytz

MADRID_TZ = pytz.timezone("Europe/Madrid")

def check_hours():
    now = datetime.now(MADRID_TZ)
    return 7 <= now.hour < 22

def anti_ban_delay():
    delay = random.uniform(3.0, 9.0)
    print(f"Delay anti-ban: {delay:.1f}s")
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
            viewport={"width":1280,"height":900},
        )
        await ctx.add_init_script("Object.defineProperty(navigator,'webdriver',{get:()=>undefined})")

        # Cargar cookies
        await ctx.add_cookies([
            {"name":"auth_token","value":auth_token,"domain":".x.com","path":"/","secure":True,"httpOnly":True,"sameSite":"None"},
            {"name":"ct0","value":ct0,"domain":".x.com","path":"/","secure":True,"sameSite":"Lax"},
        ])

        page = await ctx.new_page()
        page.set_default_timeout(20000)

        # Ir directamente a la home
        print("Abriendo x.com/home...")
        await page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=25000)
        await asyncio.sleep(4)

        url = page.url
        print(f"URL tras carga: {url}")
        if "login" in url or "i/flow" in url:
            raise Exception("Sesion expirada — exporta cookies nuevas desde tu navegador")

        tweet_id = None

        if reply_to:
            # RESPONDER a un tweet
            print(f"Respondiendo a tweet {reply_to}...")
            await page.goto(f"https://x.com/i/web/status/{reply_to}", wait_until="domcontentloaded")
            await asyncio.sleep(3)
            reply_btn = page.locator('[data-testid="reply"]').first
            await reply_btn.click(timeout=10000)
            await asyncio.sleep(2)
        else:
            # NUEVO TWEET — usar el compose box de la home directamente (tweetButtonInline)
            # NO abrir modal, escribir en el area principal de la home
            compose_area = page.locator('[data-testid="tweetTextarea_0"]').first
            if await compose_area.count() > 0:
                print("Usando compose box de la home...")
                await compose_area.click(timeout=8000)
                await asyncio.sleep(1)
            else:
                # Fallback: abrir modal con el boton de redactar
                print("Abriendo modal de redaccion...")
                new_tweet_btn = page.locator('[data-testid="SideNav_NewTweet_Button"]').first
                await new_tweet_btn.click(timeout=8000)
                await asyncio.sleep(2)
                compose_area = page.locator('[data-testid="tweetTextarea_0"]').first
                await compose_area.click(timeout=8000)
                await asyncio.sleep(1)

        # Escribir el texto
        print(f"Escribiendo: {text[:60]}...")
        await page.keyboard.type(text, delay=random.randint(30, 80))
        await asyncio.sleep(2)

        # Verificar que se escribio
        typed = await page.evaluate("""
            () => {
                const areas = document.querySelectorAll('[data-testid="tweetTextarea_0"]');
                return areas.length > 0 ? areas[0].textContent : '';
            }
        """)
        print(f"Texto en compose ({len(typed)} chars): {typed[:50]}")

        if len(typed.strip()) < 3:
            # El texto no se escribio, intentar con JS
            print("Reintentando con JS...")
            await page.evaluate(f"""
                () => {{
                    const area = document.querySelector('[data-testid="tweetTextarea_0"]');
                    if (area) {{
                        area.focus();
                        document.execCommand('insertText', false, {json.dumps(text)});
                    }}
                }}
            """)
            await asyncio.sleep(2)

        # Buscar y hacer click en el boton de publicar
        # Probar los dos selectores posibles: inline (home) y modal
        submit_btn = None
        for selector in ['[data-testid="tweetButtonInline"]', '[data-testid="tweetButton"]']:
            locator = page.locator(selector).first
            if await locator.count() > 0:
                # Esperar a que se habilite (texto escrito = botón activo)
                try:
                    await locator.wait_for(state="visible", timeout=5000)
                    # Verificar que está habilitado
                    is_disabled = await locator.get_attribute("aria-disabled")
                    print(f"Botón {selector}: aria-disabled={is_disabled}")
                    if is_disabled != "true":
                        submit_btn = locator
                        break
                except:
                    pass

        if not submit_btn:
            await page.screenshot(path="/tmp/debug_tweet.png")
            raise Exception("No se encontro el boton de publicar habilitado")

        print("Publicando...")
        # force=True para ignorar overlays (popups de cookies, etc.)
        try:
            await submit_btn.click(force=True, timeout=10000)
        except Exception:
            # Fallback: click via JavaScript
            print("Fallback: click via JS")
            await page.evaluate("""
                () => {
                    const btn = document.querySelector('[data-testid="tweetButtonInline"]')
                             || document.querySelector('[data-testid="tweetButton"]');
                    if (btn) btn.click();
                }
            """)
        await asyncio.sleep(5)

        # Obtener el ID del tweet publicado
        try:
            result = await page.evaluate("""
                () => {
                    const links = Array.from(document.querySelectorAll('a[href*="/status/"]'));
                    const ids = links.map(l => {
                        const m = l.href.match(/status\\/([0-9]+)/);
                        return m ? m[1] : null;
                    }).filter(Boolean);
                    return ids.length > 0 ? ids[ids.length-1] : null;
                }
            """)
            tweet_id = result
            print(f"Tweet ID obtenido: {tweet_id}")
        except Exception as e:
            print(f"No se pudo obtener tweet_id: {e}")
            tweet_id = "published_unknown_id"

        await browser.close()
        return tweet_id or "published"

async def main():
    text     = os.environ.get("TWEET_TEXT", "")
    reply_to = os.environ.get("REPLY_TO", "") or None
    action   = os.environ.get("ACTION", "tweet")

    if not text:
        print("ERROR: TWEET_TEXT vacio"); sys.exit(1)
    if len(text) > 280:
        text = text[:277] + "..."

    if not check_hours():
        now = datetime.now(MADRID_TZ).strftime("%H:%M")
        print(f"Fuera de horario ({now} Madrid). Esperando al horario 07:00-22:00.")
        with open("result.json","w") as f:
            json.dump({"status":"deferred","hora":now}, f)
        sys.exit(0)

    print(f"[{datetime.now(MADRID_TZ).strftime('%H:%M')} Madrid] Publicando tweet...")
    anti_ban_delay()

    tweet_id = await post_via_playwright(text, reply_to)
    url = f"https://x.com/DelphosInnova/status/{tweet_id}" if tweet_id and tweet_id != "published" else "https://x.com/DelphosInnova"

    print(f"EXITO — tweet_id: {tweet_id}")
    print(f"URL: {url}")
    with open("result.json","w") as f:
        json.dump({"tweet_id": tweet_id, "url": url, "text": text}, f)

asyncio.run(main())
