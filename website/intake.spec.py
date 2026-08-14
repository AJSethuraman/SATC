from playwright.sync_api import sync_playwright
import json as J

U = "http://localhost:8790/"
EXE = "/opt/pw-browsers/chromium-1194/chrome-linux/chrome"
STUB = """window.__posts=[];window.fetch=async(u,o)=>{const r={};
  for(const [k,v] of o.body.entries()) r[k]=(r[k]?r[k]+' | ':'')+v;
  window.__posts.push({u,r}); return {ok:true};};"""

results = []
def ok(cond, msg):
    results.append(bool(cond))
    print(("  PASS  " if cond else "  FAIL  ") + msg)

def step(pg, value=None, text=None):
    if value: pg.click("label.chip:has(input[value='%s'])" % value)
    if text:  pg.fill(".wiz-step input[type=text], .wiz-step textarea", text)
    pg.click("#intakeForm button[type=submit]")
    pg.wait_for_timeout(200)

def answers(pg):
    raw = pg.evaluate("sessionStorage.getItem('satc_intake_v1')")
    return list(J.loads(raw)["answers"].keys()) if raw else []

with sync_playwright() as p:
    b = p.chromium.launch(executable_path=EXE)

    print("\n=== BLOCKER: config reaches intake.js, Formspree POST fires ===")
    pg = b.new_page(); pg.add_init_script(STUB); pg.goto(U); pg.wait_for_timeout(400)
    ok(pg.evaluate("typeof window.SATC_CONFIG") == "object", "window.SATC_CONFIG is defined")
    for v in ["individual_tax", "w2", "current", "no"]: step(pg, v)
    step(pg)                                            # notes, optional
    pg.fill("input[name=name]", "Test Prospect"); pg.fill("input[name=email]", "t@example.com")
    pg.check("input[name=consent]")
    pg.click("#intakeForm button[type=submit]"); pg.wait_for_timeout(500)
    posts = pg.evaluate("window.__posts")
    ok(len(posts) == 1, "exactly 1 POST fired (got %d)" % len(posts))
    if posts:
        r = posts[0]["r"]
        ok("formspree.io/f/mwleqelj" in posts[0]["u"], "POST target " + posts[0]["u"])
        try:
            J.loads(r["_json"]); ok(True, "_json present and parses")
        except Exception as e:
            ok(False, "_json parse: %s" % e)
        ok(r.get("_replyto") == "t@example.com", "_replyto set to the prospect")
        ok(r.get("Name") == "Test Prospect", "Name present")
    ok("Thank you" in pg.inner_text("#intakeMount"), "thank-you rendered")
    ok(pg.evaluate("sessionStorage.getItem('satc_intake_v1')") is None, "sessionStorage cleared")
    pg.close()

    print("\n=== STALE DATA: full cascade after dropping the business service ===")
    # Walk the whole business subtree, then go back to step 1 and swap the
    # service to individual-only. Structure, complexity, headcount and revenue
    # must all vanish together — not just the one level below the change.
    pg = b.new_page(); pg.add_init_script(STUB); pg.goto(U); pg.wait_for_timeout(300)
    step(pg, "business_tax")
    step(pg, "s_corp"); step(pg, "employees"); step(pg, "500k_2m")
    print("   after business path:", answers(pg))
    for _ in range(10):
        bk = pg.query_selector("[data-back]")
        if not bk: break
        bk.click(); pg.wait_for_timeout(150)
        if "help you with" in (pg.inner_text(".wiz-q") or ""): break
    pg.click("label.chip:has(input[value='business_tax'])")        # deselect
    pg.click("label.chip:has(input[value='individual_tax'])"); pg.wait_for_timeout(250)
    after = answers(pg)
    print("   after deselect     :", after)
    for k in ["business_structure", "business_complexity", "headcount", "revenue_band"]:
        ok(k not in after, "%s cleared by cascade" % k)
    pg.close()

    print("\n=== not_yet business skips the complexity subtree ===")
    pg = b.new_page(); pg.add_init_script(STUB); pg.goto(U); pg.wait_for_timeout(300)
    step(pg, "entity_setup"); step(pg, "not_yet")
    q = pg.inner_text(".wiz-q")
    ok("does the business involve" not in q, "business_complexity skipped (next: %r)" % q[:45])
    pg.close()

    print("\n=== PROGRESS BAR never runs backwards ===")
    pg = b.new_page(); pg.add_init_script(STUB); pg.goto(U); pg.wait_for_timeout(300)
    widths = []
    for v in ["individual_tax", "business_owner"]:
        widths.append(float(pg.eval_on_selector(".wiz-bar span", "e=>parseFloat(e.style.width)")))
        step(pg, v)
    widths.append(float(pg.eval_on_selector(".wiz-bar span", "e=>parseFloat(e.style.width)")))
    print("   widths:", widths)
    ok(all(widths[i] <= widths[i+1] for i in range(len(widths)-1)), "monotonic going forward")
    pg.close()

    print("\n=== HONEYPOT does not wedge the form ===")
    pg = b.new_page(); pg.add_init_script(STUB); pg.goto(U); pg.wait_for_timeout(300)
    for v in ["individual_tax", "w2", "current", "no"]: step(pg, v)
    step(pg)
    pg.fill("input[name=name]", "Bot"); pg.fill("input[name=email]", "b@x.com")
    pg.check("input[name=consent]")
    pg.eval_on_selector("[name=_gotcha]", "e=>e.value='spam'")
    pg.click("#intakeForm button[type=submit]"); pg.wait_for_timeout(400)
    ok(len(pg.evaluate("window.__posts")) == 0, "no POST for a tripped honeypot")
    ok("Thank you" in pg.inner_text("#intakeMount"), "not stuck on a disabled Sending button")
    pg.close()

    print("\n=== CORRUPT sessionStorage does not break boot ===")
    pg = b.new_page(); errs = []
    pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(U); pg.wait_for_timeout(300)
    pg.evaluate("""sessionStorage.setItem('satc_intake_v1', JSON.stringify({
      answers:{services:'not-an-array', rental_count:{}, ghost_step:'zombie', contact:[1,2]},
      currentId:'no_such_step'}))""")
    pg.reload(); pg.wait_for_timeout(500)
    ok(not errs, "no JS errors on boot (%s)" % (errs or "none"))
    ok(pg.query_selector(".wiz-q") is not None, "still renders a step")
    pg.close()

    print("\n=== SUBMIT FAILURE keeps answers and re-enables ===")
    pg = b.new_page()
    pg.add_init_script("window.__n=0;window.fetch=async()=>{window.__n++;return {ok:false};};")
    pg.goto(U); pg.wait_for_timeout(300)
    for v in ["individual_tax", "w2", "current", "no"]: step(pg, v)
    step(pg)
    pg.fill("input[name=name]", "Fail Case"); pg.fill("input[name=email]", "f@x.com")
    pg.check("input[name=consent]")
    pg.click("#intakeForm button[type=submit]"); pg.wait_for_timeout(500)
    ok("didn" in pg.inner_text("#formStatus"), "error shown: %r" % pg.inner_text("#formStatus")[:60])
    ok(not pg.eval_on_selector("button[type=submit]", "e=>e.disabled"), "button re-enabled")
    ok(pg.eval_on_selector("input[name=name]", "e=>e.value") == "Fail Case", "answers preserved")
    for _ in range(6): pg.click("button[type=submit]")
    pg.wait_for_timeout(400)
    print("   fetch calls after 1 fail + 6 rapid clicks:", pg.evaluate("window.__n"))
    pg.close()

    print("\n=== RESET: start over, and send another ===")
    pg = b.new_page(); pg.add_init_script(STUB); pg.goto(U); pg.wait_for_timeout(400)
    ok(pg.locator("[data-reset]").count() == 0, "no Start over on a blank form")
    step(pg, "individual_tax")
    ok(pg.locator("[data-reset]").count() == 1, "Start over appears once answered")
    pg.once("dialog", lambda d: d.dismiss())
    pg.click("[data-reset]"); pg.wait_for_timeout(300)
    ok(answers(pg) != [], "cancelling the confirm keeps the answers")
    pg.once("dialog", lambda d: d.accept())
    pg.click("[data-reset]"); pg.wait_for_timeout(350)
    ok(pg.evaluate("sessionStorage.getItem('satc_intake_v1')") is None, "accepting clears storage")
    ok(pg.locator(".chip.on").count() == 0, "no selection survives the reset")
    # after a send, Send another restarts with no confirm
    for v in ["individual_tax", "w2", "current", "no"]: step(pg, v)
    step(pg)
    pg.fill("input[name=name]", "Reset Case"); pg.fill("input[name=email]", "r@x.com")
    pg.check("input[name=consent]")
    pg.click("#intakeForm button[type=submit]"); pg.wait_for_timeout(500)
    ok(pg.locator("[data-restart]").count() == 1, "Send another offered after submitting")
    pg.click("[data-restart]"); pg.wait_for_timeout(350)
    ok("What can we help you with?" in pg.inner_text(".wiz-q"), "restarts without a confirm")
    pg.close()

    print("\n=== MOBILE 390px ===")
    pg = b.new_page(viewport={"width": 390, "height": 844})
    pg.add_init_script(STUB); pg.goto(U); pg.wait_for_timeout(400)
    ok(pg.evaluate("document.documentElement.scrollWidth") <= 390, "no horizontal overflow")
    h = pg.eval_on_selector(".wiz-step .chip", "e=>e.getBoundingClientRect().height")
    ok(h >= 44, "tap target %.0fpx >= 44px" % h)
    pg.close(); b.close()

print("\n%d/%d passed" % (sum(results), len(results)))
