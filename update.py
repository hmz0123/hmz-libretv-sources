import json
import urllib.request
from datetime import datetime
from urllib.parse import urlparse

# 在这里填入你想同时拉取的所有源地址（支持无限添加）
SOURCE_URLS = [
    # 1. hmz-tvbox 在线监测源
    "https://raw.githubusercontent.com/hmz0123/hmz-tvbox/refs/heads/main/peter_tvbox_pro.json",
    # 2. hmz-ziyuanzhan 资源站
    "https://raw.githubusercontent.com/hmz0123/hmz-ziyuanzhan/refs/heads/main/docs/data/latest.json",
    # 3. hmz-tvbox02 资源站
    "https://raw.githubusercontent.com/hmz0123/hmz-tvbox02/refs/heads/master/jsm.json",
    # hmz-tvyuan
    "https://raw.githubusercontent.com/hmz0123/hmz-tvyuan/refs/heads/master/tvbox_full.json",
]

OUTPUT_FILE = "libretv-sources.json"
MAX_SOURCES = 1000  # LibreTV 单订阅上限为 1000 个源
ADULT_KEYWORDS = []

def is_valid_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
        return parsed.scheme in ("http", "https") and bool(parsed.netloc)
    except Exception:
        return False

def check_adult(name: str, extra_text: str = "") -> bool:
    text = f"{name} {extra_text}".lower()
    return any(kw.lower() in text for kw in ADULT_KEYWORDS)

def parse_items(raw_data: dict) -> list:
    """智能识别不同仓库的 JSON 结构，统一转换为标准条目"""
    extracted = []

    # 格式 A：标准 LibreTV 格式（包含 sources 数组）
    if "sources" in raw_data and isinstance(raw_data["sources"], list):
        for s in raw_data["sources"]:
            extracted.append({
                "name": str(s.get("name", "")).strip(),
                "url": str(s.get("url", "")).strip(),
                "isAdult": bool(s.get("isAdult", False)),
                "latency": 100
            })

    # 格式 B：ziyuanzhan 格式（包含 data 数组）
    elif "data" in raw_data and isinstance(raw_data["data"], list):
        for item in raw_data["data"]:
            if item.get("status", "online") not in ("online", 1, True, "1"):
                continue
            name = str(item.get("name", "")).strip()
            url = str(item.get("link") or item.get("api") or item.get("url") or "").strip()
            extra = str(item.get("category", "")) + str(item.get("type", ""))
            extracted.append({
                "name": name,
                "url": url,
                "isAdult": check_adult(name, extra),
                "latency": item.get("responseTime") or item.get("latency") or 99999
            })

    # 格式 C：TVBox 格式（包含 sites 数组，仅提取 type=1 的苹果CMS采集接口）
    elif "sites" in raw_data and isinstance(raw_data["sites"], list):
        for site in raw_data["sites"]:
            api = str(site.get("api", "")).strip()
            if site.get("type") == 1 and is_valid_url(api):
                name = str(site.get("name", "")).strip()
                extracted.append({
                    "name": name,
                    "url": api,
                    "isAdult": check_adult(name),
                    "latency": 500
                })

    return extracted

def main():
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "application/json, text/plain, */*"
    }

    all_items = []
    success_count = 0

    # 遍历所有配置的地址并拉取合并
    for url in SOURCE_URLS:
        try:
            print(f"正在拉取: {url}")
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                text = resp.read().decode("utf-8").strip()
                raw_data = json.loads(text)
                items = parse_items(raw_data)
                print(f"  -> 成功提取 {len(items)} 条数据")
                all_items.extend(items)
                success_count += 1
        except Exception as e:
            print(f"  -> 拉取失败（已自动跳过）: {e}")

    if success_count == 0:
        raise RuntimeError("所有配置的源均拉取失败！")

    # 按延迟排序，优先保留响应快的源
    all_items.sort(key=lambda x: x["latency"])

    final_sources = []
    seen_urls = set()

    for item in all_items:
        name = item["name"]
        # 统一去除末尾多余的斜杠，防止同一接口因末尾有无 '/' 导致重复
        url = item["url"].rstrip("/")

        if not name or not is_valid_url(url) or url in seen_urls:
            continue

        seen_urls.add(url)
        final_sources.append({
            "name": name,
            "url": url,
            "isAdult": item["isAdult"]
        })

        if len(final_sources) >= MAX_SOURCES:
            break

    today = datetime.now().strftime("%Y-%m-%d")
    libretv_data = {
        "name": f"自建多源聚合 ({today})",
        "version": 2,
        "sources": final_sources
    }

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(libretv_data, f, ensure_ascii=False, indent=2)

    print(f"合并完成！共成功拉取 {success_count} 个源，去重后输出 {len(final_sources)} 条有效接口。")

if __name__ == "__main__":
    main()
