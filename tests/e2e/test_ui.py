"""Arayüzü gerçek bir Chromium'da uçtan uca test eder.

Playwright kurulu değilse testler atlanır. Kurulum:
    pip install playwright && python -m playwright install chromium
"""
import os
import threading

import pytest
from werkzeug.serving import make_server

from app import app

sync_api = pytest.importorskip("playwright.sync_api")
expect = sync_api.expect


@pytest.fixture(scope="module")
def base_url():
    server = make_server("127.0.0.1", 0, app, threaded=True)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()


@pytest.fixture(scope="module")
def browser():
    with sync_api.sync_playwright() as p:
        # Yerelde hazır bir Chromium varsa onu kullan (CHROMIUM_PATH), yoksa Playwright'ınkini
        try:
            b = p.chromium.launch(executable_path=os.environ.get("CHROMIUM_PATH") or None)
        except sync_api.Error as e:
            # CI'da tarayıcı her zaman kurulu olmalı; yerelde kurulu değilse testleri atla
            if os.environ.get("CI"):
                raise
            pytest.skip(f"Chromium başlatılamadı: {e.message.splitlines()[0]}")
        yield b
        b.close()


@pytest.fixture
def page(browser, base_url):
    # Her test yeni bir bağlamla açılır: yeni çerez, yani yeni demo verisi
    context = browser.new_context(viewport={"width": 1440, "height": 900}, locale="tr-TR")
    pg = context.new_page()
    errors = []
    pg.on("pageerror", lambda e: errors.append(str(e)))
    pg.goto(base_url + "/#b2c")
    pg.wait_for_selector(".sub-panel")
    yield pg
    context.close()
    assert not errors, errors


def test_dashboard_shows_numbers_and_price_hikes(page):
    assert page.locator("h1").inner_text() == "Tekrar Hoş Geldin!"
    assert "65.000,00 ₺" in page.locator(".kpis").inner_text()
    assert "zam tespit edildi" in page.locator(".alert").inner_text()


def test_freezing_a_card_updates_savings(page):
    savings = page.locator(".kpi").nth(3)
    before = savings.locator(".sub").inner_text()
    page.click('[data-sub="netflix"] [data-action="status"]')
    page.wait_for_selector('[data-sub="netflix"] .vcard.is-frozen')
    assert "donduruldu" in page.locator("#toast").inner_text()
    assert savings.locator(".sub").inner_text() != before


def test_limit_below_price_warns_and_saves(page):
    field = page.locator('[data-limit-input="netflix"]')
    field.fill("100")
    assert page.locator('[data-sub="netflix"] .limit-warn').is_visible()
    page.click('[data-sub="netflix"] .save-btn')
    expect(page.locator("#toast")).to_contain_text("güncellendi")
    assert page.locator('[data-sub="netflix"] .card-limit').inner_text() == "100,00 ₺"


def test_deleted_card_can_be_restored(page):
    page.click('[data-sub="disney-plus"] [data-action="delete"]')
    page.wait_for_selector('[data-sub="disney-plus"]', state="detached")
    page.click(".toast-action")
    page.wait_for_selector('[data-sub="disney-plus"]')
    order = page.locator(".sub-panel").evaluate_all("els => els.map(e => e.dataset.sub)")
    assert order == ["netflix", "disney-plus", "youtube-premium"]


def test_company_dashboard_modals(page):
    page.click('.nav a[data-view="b2b"]')
    page.select_option(".select", "spotify")
    page.click('[data-action="explain"]')
    assert page.locator(".modal").is_visible()
    page.keyboard.press("Escape")
    assert page.locator(".modal").count() == 0
    page.click('[data-action="report"]')
    assert "Aylık ücret" in page.locator(".kv").inner_text()


def test_language_switch(page):
    page.click('[data-action="lang"]')
    expect(page.locator("h1")).to_have_text("Welcome back!")
    assert "₺65,000.00" in page.locator(".kpis").inner_text()
    page.click('[data-sub="netflix"] [data-action="ai"]')
    page.wait_for_selector('[data-sub="netflix"] .ai-lead')
    assert "price" in page.locator('[data-sub="netflix"] .ai-lead').inner_text()
    page.reload()
    page.wait_for_selector(".sub-panel")
    assert page.locator("h1").inner_text() == "Welcome back!"


def test_intro_stays_closed(page):
    page.click('[data-action="close-intro"]')
    assert page.locator(".intro").count() == 0
    page.reload()
    page.wait_for_selector(".sub-panel")
    assert page.locator(".intro").count() == 0


@pytest.mark.parametrize("view", ["b2c", "b2b", "islemler"])
def test_phone_layout_has_no_horizontal_scroll(browser, base_url, view):
    context = browser.new_context(viewport={"width": 390, "height": 844})
    pg = context.new_page()
    pg.goto(f"{base_url}/#{view}")
    pg.wait_for_selector(".page-head")
    assert pg.evaluate("document.documentElement.scrollWidth") <= 390
    context.close()


def test_english_uses_singular_for_one(page):
    page.click('[data-action="lang"]')
    expect(page.locator("h1")).to_have_text("Welcome back!")
    page.click('[data-sub="netflix"] [data-action="cap-limit"]')
    expect(page.locator(".alert")).to_contain_text("Price hike found on 1 subscription.")
