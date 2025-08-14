# scripts/fetch_from_template.py
import os, sys, json, hashlib, re
from pathlib import Path
import yaml
import requests
import asyncio

# 設定
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
REQUEST_TIMEOUT = 10
PLAYWRIGHT_CONCURRENCY = int(os.environ.get("PLAYWRIGHT_CONCURRENCY", "3"))  # CI負荷に合わせて調整
TEMPLATE_PATH = "urls_template.yaml"
SNAPSHOT_DIR = Path("snapshots")
MAP_PATH = SNAPSHOT_DIR / "map.json"

def slugify(s: str) -> str:
    s = re.sub(r"^https?://", "", s)
    s = re.sub(r"[^\w\-]+", "_", s)
    # 長すぎるならハッシュを付与
    if len(s) > 60:
        h = hashlib.sha1(s.encode("utf-8")).hexdigest()[:8]
        s = s[:60] + "_" + h
    return s.strip("_")

def load_template():
    with open(TEMPLATE_PATH, encoding="utf-8") as fp:
        docs = list(yaml.safe_load_all(fp))
    # docs may include None or comments; filter
    items = []
    for d in docs:
        if isinstance(d, dict) and "url" in d:
            fetch = d.get("fetch", "auto")
            url = d["url"]
            name = d.get("name") or url
            items.append({"url": url, "name": name, "fetch": fetch})
    return items

def try_requests_save(url, outpath):
    headers = {
        "User-Agent": USER_AGENT,
        "Referer": "https://www.google.com/",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    }
    try:
        r = requests.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
        print(f"[REQ] {url} -> {r.status_code}")
        if r.status_code == 200 and r.text:
            outpath.parent.mkdir(parents=True, exist_ok=True)
            outpath.write_text(r.text, encoding="utf-8")
            print(f"[REQ] saved {outpath}")
            return True
        else:
            return False
    except Exception as e:
        print(f"[REQ] error {url}: {e}", file=sys.stderr)
        return False

async def fetch_playwright_for_list(sites):
    from playwright.async_api import async_playwright
    sem = asyncio.Semaphore(PLAYWRIGHT_CONCURRENCY)

    async def worker(s):
        async with sem:
            url = s["url"]
            outpath = Path(s["out"])
            try:
                async with async_playwright() as p:
                    browser = await p.chromium.launch(headless=True, args=["--no-sandbox"])
                    context = await browser.new_context(user_agent=USER_AGENT, viewport={"width":1200,"height":900})
                    page = await context.new_page()
                    await page.goto(url, wait_until="networkidle", timeout=30000)
                    await asyncio.sleep(0.5)
                    html = await page.content()
                    outpath.parent.mkdir(parents=True, exist_ok=True)
                    outpath.write_text(html, encoding="utf-8")
                    print(f"[PW] saved {outpath}")
                    await page.close()
                    await context.close()
                    await browser.close()
            except Exception as e:
                print(f"[PW] failed {url}: {e}", file=sys.stderr)

    tasks = [asyncio.create_task(worker(s)) for s in sites]
    await asyncio.gather(*tasks)

def main():
    items = load_template()
    mapping = {}
    to_playwright = []

    for it in items:
        url = it["url"]
        slug = slugify(url)
        out = SNAPSHOT_DIR / f"{slug}.html"
        it["out"] = str(out)
        # fetch ポリシーに応じて処理
        if it["fetch"] == "requests":
            ok = try_requests_save(url, out)
            if not ok:
                print(f"[INFO] requests failed but fetch=requests -> will NOT fallback for {url}")
        elif it["fetch"] == "playwright":
            to_playwright.append(it)
        else:  # auto
            ok = try_requests_save(url, out)
            if not ok:
                to_playwright.append(it)
        mapping[url] = str(out.resolve())

    # Playwright で取得するリストがあれば並列制御で取得
    if to_playwright:
        print(f"[INFO] {len(to_playwright)} sites to fetch with Playwright")
        asyncio.run(fetch_playwright_for_list(to_playwright))
        # 上で保存されているはずだが、念のため mapping のパスを resolve して再write
        for it in to_playwright:
            mapping[it["url"]] = str(Path(it["out"]).resolve())

    # マッピングを保存
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    MAP_PATH.write_text(json.dumps(mapping, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[INFO] mapping saved to {MAP_PATH}")

if __name__ == "__main__":
    main()
