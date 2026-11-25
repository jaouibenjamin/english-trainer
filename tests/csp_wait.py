"""A wait_for_function that works under the pages' Content-Security-Policy (used by tests/play.py and tests/run.py;
not a suite of its own).

The policy forbids evaluating strings as code inside the page, which is how Playwright's wait_for_function runs its
predicate. page.evaluate is not affected (the test tool compiles it, not the page), so the wait is one evaluate of a
small loop that checks the predicate on every animation frame, as Playwright's own wait does."""
import time

LOOP = """async()=>{const end=Date.now()+%d;
 const tick=()=>new Promise(r=>{let done=0;const go=()=>{if(!done){done=1;r()}};requestAnimationFrame(go);setTimeout(go,50)});
 for(;;){const v=(%s);if(v)return v;if(Date.now()>end)return {__timeout:1};await tick()}}"""


def csp_wait(pg):
    from playwright.async_api import TimeoutError as PWTimeout
    async def wait_for_function(expression, arg=None, timeout=30000, polling=None):
        assert arg is None, 'csp_wait: a predicate with an argument is not supported'
        e = expression.strip()
        body = f'({e})()' if e.startswith(('function', '(', 'async')) and '=>' in e or e.startswith('function') else e
        t = timeout or 30000
        end = time.time() + t / 1000
        while True:
            try:
                v = await pg.evaluate(LOOP % (max(0, int((end - time.time()) * 1000)), body))
            except Exception as err:      # only a page that is being replaced is waited out; any other error is the test's
                if 'context was destroyed' not in str(err) and 'navigation' not in str(err):
                    raise
                v = None
            if v and not (isinstance(v, dict) and v.get('__timeout')):
                return v
            if time.time() >= end:
                raise PWTimeout(f'wait_for_function timed out after {t} ms: {expression[:120]}')
    pg.wait_for_function = wait_for_function
    return pg
