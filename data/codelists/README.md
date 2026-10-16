# Číselníky

| Soubor | Pole NOR | Stav |
| --- | --- | --- |
| `../mkn-10-strukturovane-podklady-20260101/…/cp_utf8/01_MKN10_5E_2026_utf8.csv` | `dg_nov` | oficiální MKN-10-CZ 2026 (ÚZIS) |
| `grading.csv` | `grade` | **provizorní** – kódy převzaty z `examples/pacient1_case.example.json` (G3 → 3, Gx → 9). Ověřit proti číselníku NOR Grading (otevřená otázka v CLAUDE.md). |

Chybí: MKN-O-3 (morfologie, topografie), TNM 8, Lateralita, Pohlavi, StanoveniDg, KlinickeStadium a další číselníky NOR.
Pole bez číselníku dostanou `Issue` CODELIST_MISSING.
