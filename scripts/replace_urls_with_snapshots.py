# scripts/replace_urls_with_snapshots.py
import json, os
from pathlib import Path
import yaml

MAP_PATH = Path("snapshots") / "map.json"
URLS_YAML = Path("urls.yaml")

def main():
    if not MAP_PATH.exists():
        print(f"[ERROR] map not found: {MAP_PATH}")
        return
    if not URLS_YAML.exists():
        print(f"[ERROR] urls.yaml not found: {URLS_YAML}")
        return

    mapping = json.loads(MAP_PATH.read_text(encoding="utf-8"))
    with open(URLS_YAML, encoding="utf-8") as fp:
        docs = list(yaml.safe_load_all(fp))

    changed = False
    new_docs = []
    cwd = Path.cwd().resolve()
    for doc in docs:
        if isinstance(doc, dict) and "url" in doc:
            orig = doc["url"]
            # exact match in mapping -> replace with file:// absolute path
            if orig in mapping:
                new_path = mapping[orig]
                file_url = "file://" + str(Path(new_path).resolve())
                print(f"[REPLACE] {orig} -> {file_url}")
                doc["url"] = file_url
                changed = True
        new_docs.append(doc)

    if changed:
        with open(URLS_YAML, "w", encoding="utf-8") as fp:
            yaml.dump_all(new_docs, fp, allow_unicode=True)
        print("[INFO] urls.yaml updated with file:// snapshots")
    else:
        print("[INFO] no changes made to urls.yaml")

if __name__ == "__main__":
    main()
