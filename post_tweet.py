#!/usr/bin/env python3
# post_tweet.py v4 - Playwright con stealth anti-deteccion completo
# 8 capas de proteccion para que X no detecte automatizacion

import os, json, asyncio, random, time, sys, re
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

async def click_with_retry(locator, timeout=8000, retries=2, wait_between=2.0):
    # Reintenta tras un TimeoutError antes de dejar que falle de verdad —
    # X a veces tarda en renderizar el boton y el click(timeout=8000) original
    # mataba todo el script sin segunda oportunidad (causa de varios runs "failure" en GH Actions).
    # A partir del 2o intento usamos force=True: la causa mas comun del timeout es un
    # <div data-testid="mask"> (overlay/dropdown residual de X) interceptando el click aunque
    # el elemento ya sea visible y este habilitado - el propio boton de publicar tweet ya usaba
    # force=True con exito, aqui aplicamos la misma tecnica al compose box y al boton de reply.
    last_exc = None
    for attempt in range(retries + 1):
        try:
            await locator.click(timeout=timeout, force=(attempt > 0))
            return
        except Exception as e:
            last_exc = e
            if attempt < retries:
                print(f"Click fallo (intento {attempt+1}), reintentando en {wait_between}s...")
                await asyncio.sleep(wait_between)
    raise last_exc

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

        # Capturar el ID real del tweet desde la respuesta de la API (CreateTweet),
        # en vez de adivinarlo rastreando el DOM — el rastreo del DOM devolvia el ID
        # del tweet padre al responder dentro de un hilo, rompiendo la cadena.
        captured_id = {"value": None}

        async def _on_response(response):
            if captured_id["value"]:
                return
            if "CreateTweet" not in response.url:
                return
            try:
                body = await response.json()
                result = body["data"]["create_tweet"]["tweet_results"]["result"]
                rest_id = result.get("rest_id") or result.get("legacy", {}).get("id_str")
                if rest_id:
                    captured_id["value"] = rest_id
            except Exception:
                pass

        page.on("response", _on_response)

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
            await click_with_retry(reply_btn)
            await asyncio.sleep(random.uniform(1, 2))
        else:
            # Usar el compose box del home
            compose = page.locator('[data-testid="tweetTextarea_0"]').first
            if await compose.count() > 0:
                await click_with_retry(compose)
            else:
                # Modal de redaccion
                btn = page.locator('[data-testid="SideNav_NewTweet_Button"]').first
                await click_with_retry(btn)
                await asyncio.sleep(random.uniform(1, 2))
                compose = page.locator('[data-testid="tweetTextarea_0"]').first
                await click_with_retry(compose)
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

        # Esperar un poco mas si la respuesta de CreateTweet aun no llego
        for _ in range(10):
            if captured_id["value"]:
                break
            await asyncio.sleep(0.5)

        tweet_id = captured_id["value"]

        if not tweet_id:
            # Fallback CONFIRMADO ROTO en produccion real (24/06): rastrear
            # CUALQUIER link /status/ de la pagina actual es muy poco fiable cuando
            # se publica desde x.com/home, porque esa pagina sigue mostrando el
            # timeline lleno de tweets de OTRAS cuentas debajo del compositor --
            # `ids[ids.length-1]` puede devolver el ID de un tweet random de otra
            # persona (confirmado: capturo un tweet de @AmericaPapaBear sin relacion
            # alguna, que ademas se uso luego como "reply_to" para el resto del hilo).
            # Fallback nuevo: ir al propio perfil (recencia garantiza que nuestro
            # tweet recien publicado es el primero) y verificar que el texto del
            # primer tweet del perfil coincide con lo que acabamos de escribir antes
            # de confiar en su ID.
            try:
                await page.goto("https://x.com/DelphosInnova", wait_until="domcontentloaded", timeout=20000)
                await page.wait_for_selector('article[data-testid="tweet"]', timeout=10000)
                await asyncio.sleep(random.uniform(1.5, 2.5))
                first_article = page.locator('article[data-testid="tweet"]').first
                own_text = (await first_article.inner_text()).lower()
                link = await first_article.locator('a[href*="/status/"]').first.get_attribute("href")
                candidate_id = None
                if link:
                    m = re.search(r"/status/(\d+)", link)
                    if m:
                        candidate_id = m.group(1)
                # Verificacion: los primeros ~20 caracteres significativos de lo que
                # escribimos deben aparecer en el primer tweet del perfil -- si no
                # coincide, el tweet recien publicado no es ese (posible delay de
                # renderizado) y es mas seguro no devolver un ID falso.
                check = re.sub(r"\s+", " ", text[:30].strip().lower())
                if candidate_id and check and check[:15] in re.sub(r"\s+", " ", own_text):
                    tweet_id = candidate_id
                    print(f"ID recuperado via perfil propio (verificado por texto): {tweet_id}")
                else:
                    print(f"Fallback perfil: texto del primer tweet del perfil no coincide -- "
                          f"esperado~'{check[:30]}' visto='{own_text[:60]}'")
            except Exception as e:
                print(f"Fallback perfil fallo: {e}")

        await browser.close()
        return tweet_id or "published"

async def post_thread(tweets: list):
    """Publica un hilo: cada tweet responde al anterior.

    Si la respuesta de X tarda/se bloquea por anti-spam, post_via_playwright cae
    al rastreo del DOM y puede devolver el ID del tweet AL QUE SE RESPONDE (no uno
    nuevo) -- eso significa que esa respuesta concreta NO se publico de verdad,
    aunque no lance excepcion. Detectarlo aqui evita reportar "hilo publicado"
    cuando en realidad solo el primer tweet llego a X.
    """
    ids = []
    broken_at = None
    reply_to = None
    for i, text in enumerate(tweets):
        if len(text) > 280: text = text[:277] + "..."
        print(f"Tweet hilo {i+1}/{len(tweets)}: {text[:50]}...")
        anti_ban_delay()
        tweet_id = await post_via_playwright(text, reply_to)

        # Sin ID fiable: o bien "published" (ni la captura de red ni la verificacion de
        # perfil pudieron confirmar un ID real) o el mismo ID del tweet padre (anti-spam
        # de X no creo la respuesta de verdad). En vez de marcar el hilo roto al primer
        # intento, reintentamos un par de veces con espera mas larga -- la mayoria de
        # bloqueos de X son temporales (rate-limit de unos segundos), no permanentes.
        def id_no_fiable(tid):
            return tid == "published" or (reply_to is not None and tid == reply_to)

        attempt = 1
        while id_no_fiable(tweet_id) and attempt <= 2:
            print(f"AVISO: tweet {i+1}/{len(tweets)} no genero ID nuevo/fiable (intento {attempt}/2) -- reintentando tras espera extra...")
            time.sleep(random.uniform(15, 25))
            tweet_id = await post_via_playwright(text, reply_to)
            attempt += 1

        if id_no_fiable(tweet_id):
            broken_at = i + 1
            ids.append(tweet_id)
            print(f"FALLO: tweet {i+1}/{len(tweets)} no genero un ID nuevo/fiable tras {attempt} intentos -- hilo roto desde aqui, se detiene la publicacion del resto para no encadenar respuestas a un ID invalido")
            break

        ids.append(tweet_id)
        reply_to = tweet_id
        if i < len(tweets)-1:
            time.sleep(random.uniform(10, 18))  # pausa mas larga: evita el anti-spam de X al responder muy rapido
    return ids, broken_at


async def retweet_via_playwright(tweet_id):
    from playwright.async_api import async_playwright
    auth_token = os.environ["X_AUTH_TOKEN"]
    ct0 = os.environ["X_CT0"]
    ua = random.choice(USER_AGENTS)
    ok = False
    error_msg = ""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox","--disable-dev-shm-usage"])
        ctx = await browser.new_context(user_agent=ua, viewport=random.choice(VIEWPORTS),
            extra_http_headers={"Accept-Language":"es-ES,es;q=0.9,en;q=0.8"})
        ctx.add_cookies([
            {"name":"auth_token","value":auth_token,"domain":".x.com","path":"/"},
            {"name":"ct0","value":ct0,"domain":".x.com","path":"/"}
        ])
        page = await ctx.new_page()
        await page.goto("https://x.com/i/web/status/"+tweet_id, wait_until="domcontentloaded", timeout=30000)
        micro_delay()
        try:
            rt_btn = page.locator("[data-testid=\"retweet\"]").first
            await rt_btn.click()
            await page.wait_for_timeout(1500)
            confirm = page.locator("[data-testid=\"retweetConfirm\"]").first
            await confirm.click()
            await page.wait_for_timeout(2000)
            # Verificacion real: tras confirmar, el boton de retweet debe quedar
            # marcado como activo (data-testid="unretweet"); si no aparece, el
            # click no surtio efecto (antes esto se reportaba "ok" igualmente).
            unretweet = page.locator("[data-testid=\"unretweet\"]").first
            ok = await unretweet.count() > 0
            print(("Retweet OK: " if ok else "Retweet NO confirmado: ") + tweet_id)
        except Exception as e:
            error_msg = str(e)
            print("Retweet error: "+error_msg)
        await browser.close()
    return ok, error_msg


async def delete_tweet_via_playwright(tweet_id):
    from playwright.async_api import async_playwright
    import re as _re
    auth_token = os.environ["X_AUTH_TOKEN"]
    ct0 = os.environ["X_CT0"]
    ua = random.choice(USER_AGENTS)
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=["--no-sandbox","--disable-dev-shm-usage"])
        ctx = await browser.new_context(user_agent=ua, viewport=random.choice(VIEWPORTS), locale="es-ES",
            extra_http_headers={"Accept-Language":"es-ES,es;q=0.9,en;q=0.8"})
        await ctx.add_cookies([
            {"name":"auth_token","value":auth_token,"domain":".x.com","path":"/",
             "secure":True,"httpOnly":True,"sameSite":"None"},
            {"name":"ct0","value":ct0,"domain":".x.com","path":"/","secure":True,"sameSite":"Lax"}
        ])
        page = await ctx.new_page()
        page.set_default_timeout(20000)
        await page.goto("https://x.com/i/web/status/"+tweet_id, wait_until="domcontentloaded", timeout=30000)
        await asyncio.sleep(random.uniform(2, 4))
        result = "error"
        try:
            # Esperar de verdad a que la SPA hidrate al menos un tweet -- en el
            # intento anterior "Total articles en la pagina: 0" sugiere que se
            # comprobo demasiado pronto (o hubo un bloqueo temporal por navegar
            # repetidamente a la misma URL en pocos minutos durante las pruebas).
            try:
                await page.wait_for_selector('article[data-testid="tweet"]', timeout=15000)
            except Exception:
                page_title = await page.title()
                body_snippet = (await page.evaluate("() => document.body.innerText || ''"))[:300]
                raise Exception(f"Ningun article cargo tras 15s. Title={page_title!r} Body={body_snippet!r}")
            await asyncio.sleep(random.uniform(1, 2))
            # La pagina del permalink puede mostrar mas tweets ademas del nuestro
            # (respuestas, citas que incrustan nuestro link/avatar dentro de SU
            # propio article, recomendados, etc.) -- 3 intentos previos de escopar
            # por link al status, por href del User-Name y por :has() del testid de
            # avatar fallaron igual (:has() busca en TODO el subarbol, incluyendo
            # tarjetas de cita incrustadas de otro usuario). En vez de seguir
            # adivinando un selector, inspeccionamos TODOS los articles de la
            # pagina y nos quedamos con el que tiene nuestro avatar como PRIMER
            # descendiente que matchea (document order = el propio, no uno
            # incrustado mas abajo en una cita).
            articles = await page.locator('article[data-testid="tweet"]').all()
            print(f"Total articles en la pagina: {len(articles)}")
            target_article = None
            own_ids_seen = []
            for i, art in enumerate(articles):
                avatar_testid = await art.evaluate(
                    """(el) => { const a = el.querySelector('[data-testid^="UserAvatar-Container-"]');
                                  return a ? a.getAttribute('data-testid') : null; }"""
                )
                own_link = await art.evaluate(
                    """(el) => { const a = el.querySelector('a[href*="/status/"][href*="/DelphosInnova/"]')
                                          || el.querySelector('time')?.closest('a');
                                  return a ? a.getAttribute('href') : null; }"""
                )
                snippet = (await art.inner_text())[:60].replace("\n", " | ")
                print(f"Article {i}: avatar={avatar_testid} | link={own_link} | texto={snippet!r}")
                if avatar_testid == "UserAvatar-Container-DelphosInnova":
                    m = re.search(r"/status/(\d+)", own_link or "")
                    if m:
                        own_ids_seen.append(m.group(1))
                    if target_article is None:
                        target_article = art
            print("IDs propios vistos en esta pagina: " + ", ".join(own_ids_seen))
            if target_article is None:
                raise Exception("Ningun article tiene UserAvatar-Container-DelphosInnova como avatar propio")
            caret = target_article.locator('[data-testid="caret"]').first
            await caret.click(timeout=8000)
            await asyncio.sleep(random.uniform(1, 2))

            # Diagnostico: que opciones de menu aparecieron de verdad (antes de
            # asumir que "Eliminar" es la correcta -- X puede usar otro texto/idioma)
            menu_texts = await page.locator('[role="menuitem"]').all_text_contents()
            print("Menu items: " + " | ".join(t.strip() for t in menu_texts if t.strip()))

            delete_item = page.locator('[role="menuitem"]').filter(
                has_text=_re.compile("Eliminar|Borrar|Delete", _re.I)
            ).first
            if await delete_item.count() == 0:
                raise Exception("No se encontro item 'Eliminar/Borrar/Delete' en el menu. Items vistos: " + " | ".join(t.strip() for t in menu_texts if t.strip()))
            await delete_item.click(timeout=8000)
            await asyncio.sleep(random.uniform(1.5, 2.5))

            # Diagnostico: contenido del dialogo de confirmacion (si existe), antes
            # de buscar el boton concreto -- decisivo para saber si el problema es el
            # selector del boton o que el dialogo nunca llego a abrirse.
            dialog_text = await page.evaluate("""
                () => {
                    const d = document.querySelector('[role="alertdialog"]') || document.querySelector('[role="dialog"]');
                    return d ? d.innerText : '';
                }
            """)
            print("Dialogo tras click en Eliminar: " + repr(dialog_text[:300]))

            # El testid del boton de confirmar puede variar; probamos varios candidatos
            # (testid, texto dentro de un dialogo, y como ultimo recurso cualquier boton
            # con ese texto en toda la pagina) y si ninguno aparece, volcamos diagnostico.
            confirm_selectors = [
                '[data-testid="confirmationSheetConfirm"]',
                '[data-testid="confirmSheetConfirm"]',
                '[role="alertdialog"] [role="button"]:has-text("Eliminar")',
                '[role="alertdialog"] [role="button"]:has-text("Borrar")',
                '[role="alertdialog"] [role="button"]:has-text("Delete")',
                '[role="dialog"] [role="button"]:has-text("Eliminar")',
                '[role="dialog"] [role="button"]:has-text("Borrar")',
                '[role="dialog"] [role="button"]:has-text("Delete")',
                'div[role="button"]:has-text("Eliminar")',
                'div[role="button"]:has-text("Borrar")',
                'div[role="button"]:has-text("Delete")',
            ]
            clicked = False
            for sel in confirm_selectors:
                loc = page.locator(sel).first
                if await loc.count() > 0:
                    try:
                        await loc.click(timeout=5000, force=True)
                        clicked = True
                        break
                    except Exception:
                        continue
            if not clicked:
                testids = await page.evaluate("""
                    () => Array.from(document.querySelectorAll('[data-testid]'))
                        .map(e => e.getAttribute('data-testid'))
                        .filter((v,i,a) => a.indexOf(v)===i)
                """)
                raise Exception("No se encontro boton de confirmar. Dialogo: " + repr(dialog_text[:200]) + " | Testids: " + ", ".join(testids[:40]))

            await page.wait_for_timeout(2000)
            print("Eliminado: "+tweet_id)
            result = "deleted"
        except Exception as e:
            print("Error eliminando "+tweet_id+": "+str(e))
            result = "error: "+str(e)
        await browser.close()
    return result


async def follow_via_playwright(usernames: list):
    """Sigue a una lista de cuentas por su @handle. Detecta si ya se sigue y lo salta."""
    from playwright.async_api import async_playwright
    auth_token = os.environ["X_AUTH_TOKEN"]
    ct0 = os.environ["X_CT0"]
    ua = random.choice(USER_AGENTS)
    results = {}
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=[
            "--no-sandbox", "--disable-dev-shm-usage", "--disable-blink-features=AutomationControlled"
        ])
        ctx = await browser.new_context(
            user_agent=ua, viewport=random.choice(VIEWPORTS), locale="es-ES",
            extra_http_headers={"Accept-Language": "es-ES,es;q=0.9,en;q=0.8"}
        )
        await ctx.add_cookies([
            {"name": "auth_token", "value": auth_token, "domain": ".x.com", "path": "/",
             "secure": True, "httpOnly": True, "sameSite": "None"},
            {"name": "ct0", "value": ct0, "domain": ".x.com", "path": "/",
             "secure": True, "sameSite": "Lax"},
        ])
        page = await ctx.new_page()
        page.set_default_timeout(20000)

        for raw in usernames:
            username = raw.strip().lstrip('@')
            if not username:
                continue
            try:
                await page.goto(f"https://x.com/{username}", wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(random.uniform(2, 4))

                follow_btn = page.locator('[data-testid$="-follow"]').first
                unfollow_btn = page.locator('[data-testid$="-unfollow"]').first

                if await follow_btn.count() > 0:
                    await follow_btn.click(timeout=8000, force=True)
                    await asyncio.sleep(random.uniform(1, 2))
                    results[username] = "followed"
                    print(f"Followed @{username}")
                elif await unfollow_btn.count() > 0:
                    results[username] = "already_following"
                    print(f"Ya siguiendo a @{username}")
                else:
                    results[username] = "button_not_found"
                    print(f"No se encontro boton follow para @{username}")
            except Exception as e:
                results[username] = f"error: {e}"
                print(f"Error siguiendo @{username}: {e}")

            anti_ban_delay(4.0, 9.0)

        await browser.close()
    return results


async def search_tweets_via_playwright(query: str, count: int = 20):
    """Busca tuits navegando la pagina real de busqueda de X e interceptando la
    respuesta GraphQL SearchTimeline que genera el propio frontend — a diferencia
    de llamar a un endpoint hardcodeado (fetch_content.py, ahora 404 porque X rota
    el query id), esto sigue funcionando aunque X cambie el id por su lado."""
    from playwright.async_api import async_playwright
    from urllib.parse import quote

    auth_token = os.environ["X_AUTH_TOKEN"]
    ct0 = os.environ["X_CT0"]
    ua = random.choice(USER_AGENTS)
    captured = {"body": None}

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=[
            "--no-sandbox", "--disable-dev-shm-usage", "--disable-blink-features=AutomationControlled"
        ])
        ctx = await browser.new_context(
            user_agent=ua, viewport=random.choice(VIEWPORTS), locale="es-ES",
            extra_http_headers={"Accept-Language": "es-ES,es;q=0.9,en;q=0.8"}
        )
        await ctx.add_cookies([
            {"name": "auth_token", "value": auth_token, "domain": ".x.com", "path": "/",
             "secure": True, "httpOnly": True, "sameSite": "None"},
            {"name": "ct0", "value": ct0, "domain": ".x.com", "path": "/",
             "secure": True, "sameSite": "Lax"},
        ])
        page = await ctx.new_page()
        page.set_default_timeout(20000)

        async def _on_response(response):
            if "SearchTimeline" not in response.url:
                return
            try:
                body = await response.json()
                if captured["body"] is None:
                    captured["body"] = body
            except Exception:
                pass

        page.on("response", _on_response)

        url = "https://x.com/search?q=" + quote(query) + "&src=typed_query&f=live"
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        except Exception as e:
            print(f"goto error: {e}")

        for _ in range(20):
            if captured["body"] is not None:
                break
            await asyncio.sleep(0.5)

        await asyncio.sleep(random.uniform(1, 2))
        await browser.close()

    tweets = []
    body = captured["body"]
    if not body:
        print("Sin respuesta SearchTimeline capturada")
        return tweets
    try:
        instructions = (body.get("data", {}).get("search_by_raw_query", {})
                        .get("search_timeline", {}).get("timeline", {}).get("instructions", []))
        for instr in instructions:
            if instr.get("type") != "TimelineAddEntries":
                continue
            for entry in instr.get("entries", []):
                if not entry.get("entryId", "").startswith("tweet-"):
                    continue
                try:
                    result = entry["content"]["itemContent"]["tweet_results"]["result"]
                    legacy = result.get("legacy") or result.get("tweet", {}).get("legacy", {})
                    user_result = (result.get("core", {}).get("user_results", {})
                                    .get("result", {})) or {}
                    # X movio screen_name de "legacy" a "core" en el objeto de usuario en algun
                    # momento de 2024-2025; probar ambas rutas (y un fallback plano por si acaso)
                    screen_name = (
                        user_result.get("core", {}).get("screen_name")
                        or user_result.get("legacy", {}).get("screen_name")
                        or user_result.get("screen_name")
                        or "unknown"
                    )
                    tweet_id = result.get("rest_id") or legacy.get("id_str", "")
                    text = legacy.get("full_text", "")
                    favorite_count = legacy.get("favorite_count", 0)
                    if not tweet_id:
                        continue
                    tweets.append({
                        "tweet_id": tweet_id, "author": screen_name, "text": text,
                        "favorite_count": favorite_count,
                        "url": f"https://x.com/{screen_name}/status/{tweet_id}",
                    })
                except Exception:
                    continue
    except Exception as e:
        print(f"Parse error: {e}")
    return tweets[:count]


async def list_profile_via_playwright(handle: str, count: int = 30):
    """Lista los tweets visibles en un perfil (requiere sesion logueada, a
    diferencia de Jina que no puede leer el timeline tras el muro de login).
    Util para encontrar el tweet_id REAL de un tweet conocido por su texto,
    cuando la busqueda (SearchTimeline) no devuelve resultados fiables."""
    from playwright.async_api import async_playwright
    auth_token = os.environ["X_AUTH_TOKEN"]
    ct0 = os.environ["X_CT0"]
    ua = random.choice(USER_AGENTS)
    results = []
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=[
            "--no-sandbox", "--disable-dev-shm-usage", "--disable-blink-features=AutomationControlled"
        ])
        ctx = await browser.new_context(
            user_agent=ua, viewport=random.choice(VIEWPORTS), locale="es-ES",
            extra_http_headers={"Accept-Language": "es-ES,es;q=0.9,en;q=0.8"}
        )
        await ctx.add_cookies([
            {"name": "auth_token", "value": auth_token, "domain": ".x.com", "path": "/",
             "secure": True, "httpOnly": True, "sameSite": "None"},
            {"name": "ct0", "value": ct0, "domain": ".x.com", "path": "/",
             "secure": True, "sameSite": "Lax"},
        ])
        page = await ctx.new_page()
        page.set_default_timeout(20000)
        await page.goto(f"https://x.com/{handle}", wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_selector('article[data-testid="tweet"]', timeout=15000)
        await asyncio.sleep(random.uniform(1.5, 2.5))

        seen_ids = set()
        scrolls = 0
        while len(results) < count and scrolls < 8:
            articles = await page.locator('article[data-testid="tweet"]').all()
            for art in articles:
                try:
                    link = await art.locator(f'a[href*="/{handle}/status/"]').first.get_attribute("href")
                    if not link:
                        continue
                    m = re.search(r"/status/(\d+)", link)
                    if not m:
                        continue
                    tid = m.group(1)
                    if tid in seen_ids:
                        continue
                    seen_ids.add(tid)
                    text_snippet = (await art.inner_text())[:200].replace("\n", " | ")
                    results.append({"tweet_id": tid, "text": text_snippet})
                except Exception:
                    continue
            if len(results) >= count:
                break
            await page.mouse.wheel(0, 2000)
            await asyncio.sleep(random.uniform(1.5, 2.5))
            scrolls += 1

        await browser.close()
    return results[:count]


async def main():
    text     = os.environ.get("TWEET_TEXT", "").strip()
    reply_to = os.environ.get("REPLY_TO", "") or None
    action   = os.environ.get("ACTION", "tweet")
    # Para hilos: tweets separados por "---"
    tweets_raw = os.environ.get("TWEETS_THREAD", "")

    # El guard de horario es anti-spam para publicaciones nuevas; no aplica a borrar
    # contenido erroneo ni a busquedas/listados (no publican nada)
    if action not in ("delete", "search", "list_profile") and not check_hours():
        now = datetime.now(MADRID_TZ).strftime("%H:%M")
        print(f"Fuera de horario ({now} Madrid, permitido 07:00-22:00)")
        with open("result.json", "w") as f:
            json.dump({"status": "deferred", "hora": now}, f)
        sys.exit(0)

    print(f"[{datetime.now(MADRID_TZ).strftime('%H:%M')} Madrid] Action={action}")

    # BUSCAR TUITS (devuelve resultados a n8n via webhook, no publica nada)
    if action == "search":
        import urllib.request as _req

        query = os.environ.get("QUERY", "").strip()
        queries_raw = os.environ.get("QUERIES", "").strip()
        callback_path = os.environ.get("CALLBACK_PATH", "").strip()
        n8n_webhook = os.environ.get("N8N_WEBHOOK", "https://n8n.teamworkz.co/webhook").rstrip("/")
        extra_raw = os.environ.get("CALLBACK_EXTRA", "").strip()

        # QUERIES (JSON: [{"tipo":"...", "query":"..."}, ...]) permite varias busquedas
        # en un solo dispatch/run, para no tener que agregar varios callbacks en n8n
        jobs = []
        if queries_raw:
            try:
                jobs = json.loads(queries_raw)
            except Exception as e:
                print(f"ERROR: QUERIES invalido: {e}"); sys.exit(1)
        elif query:
            jobs = [{"tipo": "default", "query": query}]
        else:
            print("ERROR: QUERY/QUERIES vacio"); sys.exit(1)

        all_tweets = []
        for j in jobs:
            q = (j.get("query") or "").strip()
            tipo = j.get("tipo", "default")
            if not q:
                continue
            print(f"Buscando [{tipo}]: {q}")
            tweets = await search_tweets_via_playwright(q)
            print(f"Encontrados [{tipo}]: {len(tweets)} tuits")
            for t in tweets:
                t["tipo"] = tipo
            all_tweets.extend(tweets)
            if j is not jobs[-1]:
                anti_ban_delay(2.0, 4.0)

        payload = {"jobs": jobs, "tweets": all_tweets, "count": len(all_tweets)}
        if extra_raw:
            try:
                payload["extra"] = json.loads(extra_raw)
            except Exception:
                pass

        with open("result.json", "w") as f:
            json.dump(payload, f)

        if callback_path:
            try:
                req = _req.Request(
                    n8n_webhook + "/" + callback_path.lstrip("/"),
                    data=json.dumps(payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    method="POST",
                )
                _req.urlopen(req, timeout=15)
                print(f"Callback enviado a {callback_path}")
            except Exception as e:
                print(f"Callback error: {e}")
        sys.exit(0)

    # LISTAR PERFIL (diagnostico: encontrar el tweet_id real de un tweet conocido
    # por su texto, cuando la busqueda SearchTimeline no devuelve nada fiable)
    if action == "list_profile":
        handle = os.environ.get("PROFILE_HANDLE", "DelphosInnova").strip()
        count = int(os.environ.get("PROFILE_COUNT", "30") or 30)
        results = await list_profile_via_playwright(handle, count)
        print(f"Tweets encontrados en @{handle}: {len(results)}")
        for r in results:
            print(f"  {r['tweet_id']} | {r['text'][:120]}")
        with open("result.json", "w") as f:
            json.dump({"handle": handle, "tweets": results, "count": len(results)}, f)
        sys.exit(0)

    # SEGUIR CUENTAS
    if action == "follow":
        usernames_raw = os.environ.get("FOLLOW_USERNAMES", "")
        usernames = [u.strip() for u in usernames_raw.split(",") if u.strip()]
        if not usernames:
            print("ERROR: sin usernames para seguir"); sys.exit(1)
        print(f"Siguiendo a {len(usernames)} cuentas: {usernames}")
        anti_ban_delay()
        results = await follow_via_playwright(usernames)
        print(f"EXITO — follow: {results}")
        with open("result.json", "w") as f:
            json.dump({"status": "followed", "results": results}, f)
        sys.exit(0)

    # HILO: publicar múltiples tweets en cadena
    if action == "thread" and tweets_raw:
        tweets = [t.strip() for t in tweets_raw.split("|||") if t.strip()]
        if text: tweets = [text] + tweets
        if not tweets: print("ERROR: sin tweets para hilo"); sys.exit(1)
        print(f"Publicando hilo de {len(tweets)} tweets...")
        anti_ban_delay()
        ids, broken_at = await post_thread(tweets)
        url = f"https://x.com/DelphosInnova/status/{ids[0]}" if ids else ""
        with open("result.json", "w") as f:
            json.dump({"tweet_ids": ids, "url": url, "count": len(ids), "broken_at": broken_at}, f)
        if broken_at:
            print(f"FALLO PARCIAL — hilo roto desde el tweet {broken_at}/{len(ids)}: {ids}")
            sys.exit(1)
        print(f"EXITO — hilo: {ids}")
        sys.exit(0)

    # ELIMINAR TWEET
    if action == "delete":
        tweet_id = os.environ.get("TWEET_ID", "").strip()
        if not tweet_id:
            print("ERROR: sin tweet_id para eliminar"); sys.exit(1)
        print(f"Eliminando tweet {tweet_id}...")
        anti_ban_delay()
        result = await delete_tweet_via_playwright(tweet_id)
        with open("result.json", "w") as f:
            json.dump({"status": result, "tweet_id": tweet_id}, f)
        sys.exit(0)

    # RETWEET
    if action == "retweet":
        import re
        tweet_url = os.environ.get("TWEET_URL", "") or text
        m = re.search(r"/status/(\d+)", tweet_url)
        tweet_id = m.group(1) if m else None
        if not tweet_id:
            print("ERROR: no tweet_id para retweet"); sys.exit(1)
        print("Retweeteando "+tweet_id)
        anti_ban_delay()
        ok, error_msg = await retweet_via_playwright(tweet_id)
        with open("result.json", "w") as f:
            json.dump({"status": "retweeted" if ok else "error", "tweet_id": tweet_id, "error": error_msg}, f)
        if not ok:
            print("FALLO — el retweet no quedo confirmado: "+error_msg)
            sys.exit(1)
        sys.exit(0)

    # TWEET SIMPLE
    if not text:
        print("ERROR: TWEET_TEXT vacio"); sys.exit(1)
    if len(text) > 280:
        text = text[:277] + "..."

    print(f"[{datetime.now(MADRID_TZ).strftime('%H:%M')} Madrid] Iniciando publicacion...")
    anti_ban_delay()

    tweet_id = await post_via_playwright(text, reply_to)
    # Si es una respuesta y el ID capturado es el MISMO del tweet padre, el fallback
    # de rastreo del DOM se quedo con el ID del tweet al que se respondia -- senal de
    # que la respuesta no se publico de verdad (antes esto se reportaba como exito).
    failed_reply = bool(reply_to) and tweet_id == reply_to
    url = (f"https://x.com/DelphosInnova/status/{tweet_id}"
           if tweet_id and tweet_id != "published" else "https://x.com/DelphosInnova")

    with open("result.json", "w") as f:
        json.dump({"tweet_id": tweet_id, "url": url, "text": text, "failed_reply": failed_reply}, f)

    if failed_reply:
        print(f"FALLO — la respuesta no genero un tweet nuevo (sigue siendo {tweet_id})")
        sys.exit(1)
    print(f"EXITO — tweet_id: {tweet_id}")
    print(f"URL: {url}")

asyncio.run(main())
