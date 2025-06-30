#!/usr/bin/env python3
import yaml
import requests
from bs4 import BeautifulSoup

TEMPLATE = "urls.yaml.template"
OUTPUT   = "urls.yaml"
PLACEHOLDER = "{{TITLE_PLACEHOLDER}}"

def fetch_title(url, timeout=10):
    """URL を叩いて <title> を返す。なければ空文字。"""
    try:
        resp = requests.get(url, timeout=timeout)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")
        return (soup.title.string or "").strip()
    except Exception as e:
        # 失敗したら placeholder のままにしておく
        print(f"Warning: {url} のタイトル取得でエラー: {e}")
        return ""

def main():
    # テンプレートをマルチドキュメントで読み込む
    with open(TEMPLATE, encoding="utf-8") as fp:
        docs = list(yaml.safe_load_all(fp))

    for doc in docs:
        # プレースホルダとして記載のあるものだけ置き換え
        if isinstance(doc, dict) and doc.get("name") == PLACEHOLDER:
            url = doc.get("url")
            title = fetch_title(url)
            if title:
                doc["name"] = title
            else:
                doc["name"] = url  # タイトル取得失敗時は URL を name に

    # 実ファイルを書き出し
    with open(OUTPUT, "w", encoding="utf-8") as fp:
        yaml.dump_all(docs, fp, allow_unicode=True)

if __name__ == "__main__":
    main()
