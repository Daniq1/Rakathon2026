"""Sestaví demo data pro frontend (řez 1).

Vezme examples/pacient1_case.example.json a doplní do documents[].pages skutečný
text stránek z PDF Pacienta 1 (pdfplumber) a sha256 souborů, aby šly ve frontendu
zvýrazňovat citace. Výstup: frontend/src/mock/pacient1.case.json.

pip install pdfplumber
python frontend/scripts/build_demo_case.py
"""
import hashlib
import json
from pathlib import Path

import pdfplumber

ROOT = Path(__file__).resolve().parents[2]
EXAMPLE = ROOT / "examples" / "pacient1_case.example.json"
PDF_DIR = ROOT / "data" / "Nor-pacienti_Anonymizace" / "Nor-pacienti" / "pac.1_U"
OUT = ROOT / "frontend" / "src" / "mock" / "pacient1.case.json"


def main() -> None:
    case = json.loads(EXAMPLE.read_text(encoding="utf-8"))
    for doc in case["documents"]:
        pdf = PDF_DIR / doc["source_file"]
        doc["sha256"] = hashlib.sha256(pdf.read_bytes()).hexdigest()
        doc["mime"] = "application/pdf"
        with pdfplumber.open(pdf) as p:
            doc["pages"] = [
                {"page": i, "text": page.extract_text() or ""}
                for i, page in enumerate(p.pages, 1)
            ]

    # Kontrola: každá citace v ukázce musí být v textu stránky (pravidlo 1).
    pages = {
        (d["doc_id"], pg["page"]): pg["text"]
        for d in case["documents"]
        for pg in d["pages"]
    }
    for fact in case["facts"]:
        for ev in fact["evidence"]:
            text = pages.get((ev["doc_id"], ev["page"]), "")
            if ev["quote"] not in text:
                print(f"VAROVÁNÍ: citace faktu {fact['fact_id']} není v {ev['doc_id']} s.{ev['page']}")

    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(case, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Zapsáno {OUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
