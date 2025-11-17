from playwright.sync_api import sync_playwright
import time, random

class BrowserCtx:
    def __init__(self, engine="firefox", headless=True):
        self.engine = engine
        self.headless = headless
        self._p = None
        self._browser = None
        self._ctx = None

    def __enter__(self):
        self._p = sync_playwright().start()
        self._browser = getattr(self._p, self.engine).launch(headless=self.headless)
        self._ctx = self._browser.new_context()
        return self._ctx

    def __exit__(self, exc_type, exc, tb):
        if self._ctx: self._ctx.close()
        if self._browser: self._browser.close()
        if self._p: self._p.stop()

def polite_wait(seconds=2.5):
    time.sleep(seconds + random.random())
