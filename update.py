import json
import urllib.request
from urllib.parse import urlparse

SOURCE_URL = "https://github.io"
OUTPUT_FILE = "libretv-sources.json"
ADULT_KEYWORDS = ["18", "成人", "福利", "色", "伦理", "AV", "Porn", "Sex", "番号", "无码", "有码"]

def is_valid_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False

def check_adult(name: str, item: dict) -> bool:
    category = str(item.get("category", "")) + str(item.get("type", "")) + str(item.get("tags", ""))
    text = f"{name} {category}".lower()
    return any(kw.lower() in text for kw in ADULT_KEYWORDS)

def main():
    req = urllib.request.Request(SOURCE_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as resp:
        raw_data = json.loads(resp.read().decode("utf-8"))

    items = raw_data.get("data", [])
    items.sort(key=lambda x: x.get("responseTime") or x.get("latency") or 99999)

    sources = []
    seen_urls = set()

    for item in items:
        name = str(item.get("name", "")).strip()
        url = str(item.get("link") or item.get("api") or item.get("url") or "").strip()

        if not name or not is_valid_url(url) or url in seen_urls:
            continue

        seen_urls.add(url)
        sources.append({
            "name": name,
            "url": url,
            "isAdult": check_adult(name, item)
        })

        if len(sources) >= 100:
            break

    libretv_data = {
        "name": f"自建自动更新源 ({raw_data.get('updatedAt', '每日同步')})",
        "version": 2,
        "sources": sources
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(libretv_data, f, ensure_ascii=False, indent=2)

    print(f"成功生成 {len(sources)} 个有效源")

if __name__ == "__main__":
    main()
