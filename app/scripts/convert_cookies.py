import json
from pathlib import Path

def map_samesite(v: str):
    v = (v or "").lower()
    if v in ["lax", "strict", "none"]:
        return v.capitalize()
    return "Lax"  # default

def main():
    project_root = Path(__file__).resolve().parents[2]
    data_dir = project_root / "data"
    inp = data_dir / "cookies.json"
    out = data_dir / "cookies_playwright.json"

    raw = json.load(open(inp, "r", encoding="utf-8"))

    converted = []
    for c in raw:
        # EditThisCookie sometimes uses "domain": "x.com" or ".x.com"
        domain = c.get("domain", "")
        if domain and not domain.startswith("."):
            domain = "." + domain

        pc = {
            "name": c.get("name", ""),
            "value": c.get("value", ""),
            "domain": domain,
            "path": c.get("path", "/"),
            "httpOnly": bool(c.get("httpOnly", False)),
            "secure": bool(c.get("secure", True)),
            "sameSite": map_samesite(c.get("sameSite", "Lax")),
        }

        # expires: EditThisCookie sometimes has expirationDate (seconds)
        exp = c.get("expirationDate")
        if exp:
            pc["expires"] = int(exp)

        # skip empty
        if pc["name"] and pc["value"]:
            converted.append(pc)

    with open(out, "w", encoding="utf-8") as f:
        json.dump(converted, f, ensure_ascii=False, indent=2)

    print(f"✅ Dönüştürüldü: {out}")
    print(f"✅ Cookie sayısı: {len(converted)}")

if __name__ == "__main__":
    main()
