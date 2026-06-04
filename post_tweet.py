#!/usr/bin/env python3
# post_tweet.py v4 - Playwright con stealth anti-deteccion completo
# 8 capas de proteccion para que X no detecte automatizacion

import os, json, asyncio, random, time, sys
from datetime import datetime
import pytz

MADRID_TZ  = pytz.timezone("Europe/Madrid")
MAX_DAILY  = 50

# ── CAPA 1: Variedad de User-Agents (rotar entre versiones reales de Chrome) ──
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
]

# ── CAPA 2: Viewports variados (no siempre el mismo tamaño) ──
VIEWPORTS = [
    {"width": 1280, "height": 800},
    {"width": 1440, "height": 900},
    {"width": 1366, "height": 768},
    {"width": 1920, "height": 1080},
]

def check_hours():
    now = datetime.now(MADRID_TZ)
    return 7 <= now.hour < 22

def anti_ban_delay(min_s=3.0, max_s=10.0):
    # CAPA 3: Delays aleatorios con distribucion normal (mas humano que uniform)
    delay = random.gauss((min_s + max_s) / 2, (max_s - min_s) / 4)
    delay = max(min_s, min(max_s, delay))
    print(f"Delay: {delay:.1f}s")
    time.sleep(delay)

def micro_delay():
    # Pequenos delays entre acciones (100-400ms)
    time.sleep(random.uniform(0.1, 0.4))

async def human_type(page, text: str):
    # CAPA 4: Tipeo humano con velocidad variable y errores ocasionales
    for char in text:
        # Velocidad variable: mas rapido en caracteres comunes, lento en especiales
        if char in ' ,.!?':
            delay = random.randint(80, 200)
        elif char.isupper():
            delay = random.randint(60, 150)
        else:
            delay = random.randint(30, 100)
        await page.keyboard.type(char, delay=delay)
        # Pausa ocasional (como pensar antes de escribir)
        if random.random() < 0.05:
            await asyncio.sleep(random.uniform(0.3, 0.8))

async def simulate_human_behavior(page):
    # CAPA 5: Simular comportamiento humano antes de publicar
    # Scroll aleatorio para que parezca que estamos leyendo el timeline
    await page.mouse.move(random.randint(300, 900), random.randint(200, 600))
    await asyncio.sleep(random.uniform(0.5, 1.5))
    # Pequeno scroll
    await page.mouse.wheel(0, random.randint(100, 300))
    await asyncio.sleep(random.uniform(0.3, 0.8))
    await page.mouse.wheel(0, -random.randint(50, 150))
    await asyncio.sleep(random.uniform(0.5, 1.0))

async def post_via_playwright(text: str, reply_to: str = None):
    from playwright.async_api import async_playwright

    auth_token = os.environ["X_AUTH_TOKEN"]
    ct0        = os.environ["X_CT0"]

    # CAPA 6: Rotar User-Agent y Viewport en cada ejecucion
    ua       = random.choice(USER_AGENTS)
    viewport = random.choice(VIEWPORTS)
    print(f"UA: {ua[:50]}... | Viewport: {viewport['width']}x{viewport['height']}")

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
                # CAPA 7: Argumentos que ocultan que es headless
                "--disable-infobars",
                "--window-size=1920,1080",
                "--start-maximized",
                f"--user-agent={ua}",
            ]
        )
        ctx = await browser.new_context(
            user_agent=ua,
            viewport=viewport,
            locale="es-ES",
            timezone_id="Europe/Madrid",
            # CAPA 7 cont: Permisos y propiedades de navegador real
            permissions=["notifications"],
            color_scheme="light",
            extra_http_headers={
                "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT": "1",
            }
        )

        # CAPA 8: Script de stealth - ocultar que es Playwright/headless
        await ctx.add_init_script("""
            // Eliminar rastros de webdriver
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});

            // Fingerprint de plugins como Chrome real
            Object.defineProperty(navigator, 'plugins', {
                get: () => [
                    {filename: 'internal-pdf-viewer', description: 'Portable Document Format'},
                    {filename: 'mhjfbmdgcfjbbpaeojofohoefgiehjai', description: 'Chromium PDF Plugin'},
                ]
            });

            // Lenguajes como navegador real
            Object.defineProperty(navigator, 'languages', {get: () => ['es-ES', 'es', 'en']});

            // Chrome objeto presente
            window.chrome = {runtime: {}, loadTimes: () => {}, csi: () => {}};

            // Ocultar que es headless
            const originalQuery = window.navigator.permissions.query;
            window.navigator.permissions.query = (params) => {
                if (params.name === 'notifications') return Promise.resolve({state: 'default'});
                return originalQuery(params);
            };
        """)

        await ctx.add_cookies([
            {"name": "auth_token", "value": auth_token, "domain": ".x.com", "path": "/",
             "secure": True, "httpOnly": True, "sameSite": "None"},
            {"name": "ct0", "value": ct0, "domain": ".x.com", "path": "/",
             "secure": True, "sameSite": "Lax"},
        ])

        page = await ctx.new_page()
        page.set_default_timeout(25000)

        # Ir a X
        print("Abriendo x.com/home...")
        await page.goto("https://x.com/home", wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(random.uniform(3, 5))

        url = page.url
        print(f"URL: {url}")
        if "login" in url or "i/flow" in url:
            raise Exception("Sesion expirada — exporta cookies nuevas desde tu navegador")

        # Simular comportamiento humano
        await simulate_human_behavior(page)

        if reply_to:
            print(f"Respondiendo a {reply_to}...")
            await page.goto(f"https://x.com/i/web/status/{reply_to}",
                            wait_until="domcontentloaded")
            await asyncio.sleep(random.uniform(2, 4))
            reply_btn = page.locator('[data-testid="reply"]').first
            await reply_btn.click(timeout=8000)
            await asyncio.sleep(random.uniform(1, 2))
        else:
            # Usar el compose box del home
            compose = page.locator('[data-testid="tweetTextarea_0"]').first
            if await compose.count() > 0:
                await compose.click(timeout=8000)
            else:
                # Modal de redaccion
                btn = page.locator('[data-testid="SideNav_NewTweet_Button"]').first
                await btn.click(timeout=8000)
                await asyncio.sleep(random.uniform(1, 2))
                compose = page.locator('[data-testid="tweetTextarea_0"]').first
                await compose.click(timeout=8000)
            await asyncio.sleep(random.uniform(0.5, 1.5))

        # Tipeo humano
        print(f"Escribiendo ({len(text)} chars): {text[:60]}...")
        await human_type(page, text)
        await asyncio.sleep(random.uniform(1.5, 3.0))

        # Verificar texto escrito
        typed = await page.evaluate("""
            () => document.querySelector('[data-testid="tweetTextarea_0"]')?.textContent || ''
        """)
        print(f"Texto confirmado ({len(typed)} chars)")

        if len(typed.strip()) < 3:
            # Fallback con execCommand
            await page.evaluate(
                f"document.querySelector('[data-testid=\"tweetTextarea_0\"]')?.focus()"
            )
            await page.keyboard.type(text)
            await asyncio.sleep(2)

        # Mover el raton hacia el boton antes de pulsar (mas humano)
        submit_selector = '[data-testid="tweetButtonInline"]'
        try:
            btn_box = await page.locator(submit_selector).first.bounding_box()
            if btn_box:
                await page.mouse.move(
                    btn_box['x'] + btn_box['width'] / 2 + random.randint(-5, 5),
                    btn_box['y'] + btn_box['height'] / 2 + random.randint(-3, 3)
                )
                await asyncio.sleep(random.uniform(0.3, 0.7))
        except:
            pass

        # Click con force y fallback JS
        print("Publicando...")
        try:
            await page.locator(submit_selector).first.click(force=True, timeout=8000)
        except:
            await page.evaluate("""
                () => {
                    const b = document.querySelector('[data-testid="tweetButtonInline"]')
                           || document.querySelector('[data-testid="tweetButton"]');
                    if (b) b.click();
                }
            """)

        await asyncio.sleep(random.uniform(4, 6))

        # Obtener tweet_id
        tweet_id = await page.evaluate("""
            () => {
                const links = Array.from(document.querySelectorAll('a[href*="/status/"]'));
                const ids = links.map(l => {
                    const m = l.href.match(/\\/status\\/([0-9]+)/);
                    return m ? m[1] : null;
                }).filter(Boolean);
                return ids.length > 0 ? ids[ids.length - 1] : null;
            }
        """)

        await browser.close()
        return tweet_id or "published"

async def main():
    text     = os.environ.get("TWEET_TEXT", "").strip()
    reply_to = os.environ.get("REPLY_TO", "") or None
    action   = os.environ.get("ACTION", "tweet")

    if not text:
        print("ERROR: TWEET_TEXT vacio"); sys.exit(1)
    if len(text) > 280:
        text = text[:277] + "..."

    if not check_hours():
        now = datetime.now(MADRID_TZ).strftime("%H:%M")
        print(f"Fuera de horario ({now} Madrid, permitido 07:00-22:00)")
        with open("result.json", "w") as f:
            json.dump({"status": "deferred", "hora": now}, f)
        sys.exit(0)

    print(f"[{datetime.now(MADRID_TZ).strftime('%H:%M')} Madrid] Iniciando publicacion...")
    anti_ban_delay()

    tweet_id = await post_via_playwright(text, reply_to)
    url = (f"https://x.com/DelphosInnova/status/{tweet_id}"
           if tweet_id and tweet_id != "published" else "https://x.com/DelphosInnova")

    print(f"EXITO — tweet_id: {tweet_id}")
    print(f"URL: {url}")
    with open("result.json", "w") as f:
        json.dump({"tweet_id": tweet_id, "url": url, "text": text}, f)

asyncio.run(main())
