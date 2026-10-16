"""Vytáhne z MKN-10-CZ 2026 kódy novotvarů (C00–D48) pro našeptávač ve frontendu.

Jen platné položky (prázdné PlatnostDo). Výstup: frontend/src/mock/mkn10_novotvary.json
ve tvaru [{"code": "C163", "dotted": "C16.3", "label": "ZN – antrum pyloricum"}].

python frontend/scripts/build_codelists.py
"""
import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = (
    ROOT / "data" / "mkn-10-strukturovane-podklady-20260101"
    / "mkn10_strukturovane_podklady_20260101" / "cp_utf8" / "01_MKN10_5E_2026_utf8.csv"
)
OUT = ROOT / "frontend" / "src" / "mock" / "mkn10_novotvary.json"


def is_neoplasm(code: str) -> bool:
    return code[0] == "C" or (code[0] == "D" and code[1:3].isdigit() and int(code[1:3]) <= 48)


def main() -> None:
    rows = []
    with SRC.open(encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f, delimiter=";"):
            if r["PlatnostDo"] or not is_neoplasm(r["Kod"]):
                continue
            rows.append({"code": r["Kod"], "dotted": r["KodSTeckou"], "label": r["Nazev"]})
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rows, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(f"Zapsáno {len(rows)} kódů do {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
