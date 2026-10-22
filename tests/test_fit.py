"""The fit: short content is spread down to a common foot, the type never changes."""
import pytest

pytest.importorskip("playwright.sync_api")
from playwright.sync_api import sync_playwright  # noqa: E402

from renderer.shoot import FIT_CAP, FIT_MARGIN, SLIDE_H, SLIDE_W, _FIT  # noqa: E402


def _slide(block_px: int, blocks: int = 2) -> str:
    """A centred stage — title, then `blocks` boxes of `block_px` — above a page number at 1268."""
    boxes = "".join(f'<div class="b" data-gap style="height:{block_px}px;margin-top:20px"></div>'
                    for _ in range(blocks))
    return f"""<html><body style="margin:0"><div class="slide" style="position:relative;width:{SLIDE_W}px;
      height:{SLIDE_H}px;display:flex;flex-direction:column">
      <div class="stage" data-fit style="flex:1;display:flex;flex-direction:column;justify-content:center;
        padding:110px 0 120px"><h1 class="t" style="margin:0;height:80px">T</h1>{boxes}</div>
      <div class="slide-num" style="position:absolute;top:1268px">1 / 9</div></div></body></html>"""


@pytest.fixture(scope="module")
def page():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        pg = browser.new_page(viewport={"width": SLIDE_W, "height": SLIDE_H})
        yield pg
        browser.close()


def _fit(page, html):
    page.set_content(html)
    top0 = page.eval_on_selector(".t", "e => e.getBoundingClientRect().top")
    add = page.evaluate(_FIT, [FIT_MARGIN, FIT_CAP])
    top1 = page.eval_on_selector(".t", "e => e.getBoundingClientRect().top")
    bottom = page.evaluate("() => Math.max(...[...document.querySelectorAll('.b')].map(b => b.getBoundingClientRect().bottom))")
    sizes = page.evaluate("() => [...document.querySelectorAll('.b')].map(b => b.getBoundingClientRect().height)")
    return add, top0, top1, bottom, sizes


def test_short_content_reaches_the_common_foot_title_unmoved(page):
    add, top0, top1, bottom, sizes = _fit(page, _slide(380))
    assert 0 < add <= FIT_CAP
    assert top1 == pytest.approx(top0, abs=0.5)             # the title stays where it was
    assert bottom == pytest.approx(1268 - FIT_MARGIN, abs=1)
    assert sizes == [380, 380]                              # spacing only: nothing is resized


def test_each_gap_is_capped(page):
    add, top0, top1, bottom, _ = _fit(page, _slide(80))
    assert add == FIT_CAP and top1 == pytest.approx(top0, abs=0.5)
    assert bottom < 1268 - FIT_MARGIN                       # the rest stays at the foot


def test_full_slide_is_left_as_is(page):
    add, top0, top1, *_ = _fit(page, _slide(520))
    assert add == 0 and top1 == pytest.approx(top0, abs=0.5)


def test_applied_once(page):
    page.set_content(_slide(300))
    assert page.evaluate(_FIT, [FIT_MARGIN, FIT_CAP]) > 0
    assert page.evaluate(_FIT, [FIT_MARGIN, FIT_CAP]) == 0  # saved HTML shot again: no second helping
