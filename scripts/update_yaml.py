import yaml, requests
from bs4 import BeautifulSoup

PLACEHOLDER = "{{TITLE_PLACEHOLDER}}"

def fetch_title(url, timeout=10):
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
    }
    try:
        resp = requests.get(url, headers=headers, timeout=timeout)
        print(f"[DEBUG] {url} → status {resp.status_code}")
        resp.raise_for_status()
        # HTMLが返ってきているか先頭だけ確認
        print(f"[DEBUG] html[0:200]: {resp.text[:200]!r}")
        soup = BeautifulSoup(resp.text, "html.parser")
        title = (soup.title.string or "").strip()
        print(f"[DEBUG] extracted title: {title!r}")
        return title or ""
    except Exception as e:
        print(f"[WARNING] {url} タイトル取得失敗: {e}")
        return ""

def main():
    with open("urls.yaml.template", encoding="utf-8") as fp:
        docs = list(yaml.safe_load_all(fp))

    for doc in docs:
        if isinstance(doc, dict) and doc.get("name") == PLACEHOLDER:
            url = doc["url"]
            title = fetch_title(url)
            doc["name"] = title if title else url

    with open("urls.yaml", "w", encoding="utf-8") as fp:
        yaml.dump_all(docs, fp, allow_unicode=True)

if __name__ == "__main__":
    main()
