# CLAUDE.md – AI NOR (Rakathon 2026, zadání FN Ostrava)

Tento soubor čte Claude Code i GitHub Copilot (stejný obsah je v `.github/copilot-instructions.md`).
Popisuje, co stavíme, jak, a jaká pravidla nesmíš porušit. Při nejasnosti se zeptej, nehádej.

## 1. Co stavíme

Nástroj, který z onkologické dokumentace (ambulantní zprávy, histologie, propouštěcí zprávy; PDF nebo sken)
vytěží údaje pro hlášení **Incidence zhoubného novotvaru** do Národního onkologického registru (NOR),
nabídne je lékaři ke kontrole a úpravě a vyexportuje **XML ve formátu DASTA DS4 (`ds_idu_nor`)**.

Tok dat:

```
soubor → Document (syrový text po stránkách) → Fact (kandidát hodnoty + doslovná citace)
       → NorCase.fields (zvolená hodnota pro každé pole NOR) → kontrola lékařem → XML export
```

Hodnoticí kritéria zadavatele (aplikace je musí umět ukázat a změřit):
přesnost vytěžení, úplnost (povinné položky vyplněné nebo označené jako chybějící), správné přiřazení
do pole NOR, dohledatelnost zdroje, počet oprav uživatelem, čas na záznam.

## 2. Nepřekročitelná pravidla

1. **Každá vytěžená hodnota má doslovnou citaci ze zdroje** (`Evidence.quote`). Backend ověří, že citace
   v textu stránky skutečně je (`quote_verified`). Neověřená citace = nízká jistota, nikdy auto-vyplnění.
2. **LLM nevymýšlí kódy.** Kódy (MKN-10, MKN-O-3, TNM, číselníky NOR) vybírá pouze ze seznamu kandidátů,
   které vygeneruje vyhledávání v číselníku. Kód mimo číselník je chyba.
3. **Chybějící ≠ negativní ≠ suspektní.** Rozlišuj `assertion`: affirmed / negated / suspected / historical /
   unknown. „Suspektní“ nebo „k vyloučení“ není diagnóza. Co v dokumentaci není, je `status: missing`.
4. **Čas má význam.** Stadium a TNM při diagnóze (před léčbou) nejsou totéž co stav po neoadjuvanci
   (`temporal`). Nikdy neber „poslední zmíněnou hodnotu“ automaticky.
5. **Nic se tiše nepřepisuje.** Každá změna jde do `audit` (kdo, kdy, staré → nové). Konflikty se nezahazují,
   ukazují se jako `Issue`.
6. **Do LLM jde jen pseudonymizovaný text.** RČ, jména, adresy, telefony nahraď před odesláním
   (např. „Pacient 1“, `[RC]`). RČ zůstává jen jako klíč v databázi.
7. **Žádná tajemství v repu.** Klíče jen v `.env` (v `.gitignore`), GitHub Secrets a secretech Container Apps.
8. **Jen syntetická / anonymizovaná data.** Žádná reálná pacientská data.

## 3. Smlouva mezi moduly

Jediný zdroj pravdy o datech: `schema/nor_case.schema.json` (JSON Schema 2020-12, verze 0.1.0).
Ukázka validní instance: `examples/pacient1_case.example.json`.

- Názvy polí NOR = názvy atributů `nor_dg` z XSD DASTA (`dgType`). Seznam polí, povinnost v XSD
  a potřebný číselník jsou v `$defs.NorFieldName.x-nor-fields`.
- Backend: Pydantic v2 modely odpovídající schématu v `backend/app/models.py`
  (lze generovat `datamodel-code-generator`). Frontend: TypeScript typy generované
  `json-schema-to-typescript` do `frontend/src/types/nor.ts`.
- Změna schématu = PR, zvýšení `schema_version`, úprava příkladu, regenerace typů. Nikdy potichu.
- Test `tests/test_schema.py` validuje příklad proti schématu; musí vždy procházet.

## 4. Stack a struktura repa

- Backend: Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2, pdfplumber (text PDF), pytesseract + `ces` (skeny,
  fallback), rapidfuzz (fuzzy shoda s číselníky), lxml (XML + validace XSD), openai SDK (LLM přes APIM), pytest.
- Databáze: přes SQLAlchemy a `DATABASE_URL`. Výchozí SQLite (`sqlite:///data/ainor.db`), cílově
  InterSystems IRIS for Health (`iris://…`, balík `sqlalchemy-iris`). Žádný kód specifický pro jednu DB.
- Frontend: React + TypeScript + Vite, bez těžkých UI knihoven; grafy jen pokud budou potřeba.
- Nasazení: jeden kontejner – FastAPI servíruje sestavený frontend na `/` a API na `/api`.
  Lokálně `docker compose up --build`, v Azure stejný image v Container Apps.

```
backend/app/
  main.py            FastAPI app, mount frontendu
  models.py          Pydantic modely podle schématu
  api/               routery: patients, documents, cases, export, metrics
  ingest/            načtení souboru, text po stránkách, OCR fallback, hash, pseudonymizace
  extract/           regex extraktory + LLM extraktor, ověření citací
  codelists/         načítání CSV číselníků, hledání kandidátů
  resolve/           výběr hodnoty pro pole z více faktů, výpočty (y, dg_stan, metastáze, stadium)
  rules/             kontroly → Issue
  confidence.py      složené skóre a pásma
  export/            XML DASTA + validace XSD
  llm/               klient, prompty (verzované soubory), cache
  db/                SQLAlchemy tabulky a repozitáře
frontend/src/        dashboard
schema/  examples/   smlouva a ukázka
data/codelists/      číselníky (CSV, v repu)
data/synthetic/      syntetické zprávy (PDF/TXT, v repu)
data/raw/ data/cache/  nahrané soubory a cache LLM (v .gitignore)
xsd/                 oficiální XSD DASTA pro NOR (stáhnout z ciselniky.dasta.mzcr.cz)
eval/                gold standard + evaluační skript
tests/
```

## 5. Backend – pipeline

### 5.1 Ingest
- `POST /api/documents` (multipart, více souborů) → uloží originál do `data/raw/`, spočítá `sha256`.
- Text: nejdřív textová vrstva PDF (pdfplumber). Prázdná stránka → OCR (Tesseract `ces`), nastav
  `extraction_method` a `ocr_confidence`. Ukázkové PDF v `data/synthetic/` mají textovou vrstvu.
- Typ dokumentu (`doc_type`) z hlavičky („Ambulantní zpráva“, „Propouštěcí zpráva“, „Histologie“…).
- RČ z hlavičky → `patient_key` (jen číslice). Validace RČ: 9/10 číslic, platné datum (u žen měsíc +50),
  10místné dělitelné 11. Při `APP_MODE=test` neplatné RČ jen `Issue` RC_INVALID (info), nezastaví zpracování.
- Pseudonymizace před LLM (pravidlo 6). Mapování pseudonymů drž jen v backendu.

### 5.2 Extrakce
Dvě vrstvy, výsledky se slučují do `Fact`:
1. **Regex (deterministicky, levně, vysoká jistota):** MKN-10 (`C\d{2}\.?\d?`), morfologie
   (`M?\d{4}/?\d` → 5 číslic, např. `M81403` → `81403`), TNM s prefixy (`c`, `p`, `yp`, `r`) včetně
   písmen (`4a`, `3b`), uzliny („LU 24/19“, „počet a stav mízních uzlin: 24/19“ → vyšetřené 24,
   pozitivní 19; menší číslo = pozitivní), data (`d.m.rr`, `m/rr`, `rrrr`).
2. **LLM (to, co regex nezvládne):** histologický typ slovně, grading, lateralita, datum a způsob stanovení
   diagnózy, metastázy, léčba, negace a suspekce. Výstup jen JSON podle schématu faktu, `temperature=0`,
   prompt v `llm/prompts/<nazev>_v<N>.md`, `prompt_version` se ukládá k faktu.
- Každý fakt projde ověřením citace. Neověřený fakt zůstane, ale s nízkou jistotou.
- Ukládej i surovou odpověď LLM (ladění, audit).

### 5.3 Číselníky
- Načítání CSV z `data/codelists/` (MKN-10-CZ 2026 je k dispozici; další číselníky NOR doplníme).
- Kandidáti pro každý fakt: přesná shoda kódu → fuzzy shoda názvu (rapidfuzz) → abecední seznam novotvarů
  MKN-10 (termín → kód). Výsledek `codelist_candidates` (top 5 se skóre).
- Pokud je kandidátů víc a skóre blízko, LLM vybere jeden **z tohoto seznamu** (pravidlo 2).
- Chybí-li číselník pro pole, pole zůstane s `value_raw` a `Issue` CODELIST_MISSING. Nevymýšlej kódy.

### 5.4 Resolve (výběr hodnoty pro pole)
- Více faktů pro jedno pole: shodné → vyšší jistota (`cross_doc_agreement`); rozdílné → `status: conflict`,
  vyber podle pravidel níže, ostatní do `alternative_fact_ids`, vytvoř `Issue` CONFLICT_VALUE.
- `grade`: preferuj předléčebnou biopsii, pokud resekát po neoadjuvanci uvádí Gx/„x“.
- `t`, `n`, `m`: klinické TNM před léčbou. `pt`, `pn`, `pm`: patologické. `ptnmy = true`, pokud je prefix `yp`.
- `pvu`, `ppu`: z počtu uzlin. `psu`: sentinelová uzlina, jen pokud je zmíněna.
- `dg_stan`: součet kódů vyšetření (01 klinické, 02 laboratoř/markery, 04 cytologie, 08 histologie metastázy,
  16 histologie primárního nádoru) – ověřit proti číselníku StanoveniDg.
- `metastaze`: součet kódů lokalizací (1 plíce, 2 kostní dřeň, 4 kost, 8 pleura, 16 játra, 32 peritoneum,
  64 mozek, 128 nadledviny, 256 uzliny, 512 kůže, 1024 jiný orgán; 0 neznámo).
- `dat_dg`: nejčasnější datum histologického (jinak cytologického, jinak klinického) potvrzení.
  Nepřesné datum (jen měsíc/rok) → `PartialDate` + `Issue` DATE_IMPRECISE (XSD vyžaduje celé datum).
- `stadium`: vypočítat z TNM tabulkou TNM 8 v `data/stage_tables/` jen pro podporované lokalizace
  (začni žaludek, prs, kolorektum); jinak `missing` k ručnímu doplnění. Tabulky ověří klinický mentor.
- `pohlavi`: z RČ (měsíc +50 = žena); pokud RČ neplatné, z textu („pacientka“, „poučena“, „menopausa“).
  Rozpor → `Issue` SEX_CONFLICT.
- Administrativní pole (`hzz`, `hodd`, `htyp`, `hdatum`, `lekar`, `idzz`, `obec`, `zeme`…) se nevytěžují
  z textu: `source: admin`, výchozí hodnoty z konfigurace pracoviště, editovatelné v UI.

### 5.5 Pravidla (rules/ → Issue)
Minimum: MISSING_REQUIRED (povinné pole XSD bez hodnoty, `error`), CONFLICT_VALUE, DATE_IMPRECISE,
RC_INVALID, SEX_CONFLICT, CODELIST_MISSING, TNM_STAGE_MISMATCH (uvedené stadium ≠ vypočtené),
TOPO_MORPHO_INCOMPATIBLE (topografie × morfologie), DGSTAN_INCONSISTENT (`morfo_metoda=H`, ale `dg_stan`
neobsahuje 16), DATE_ORDER (léčba před diagnózou), DIAGNOSIS_SUSPECTED_ONLY (jen „suspektní“).
Každé pravidlo = funkce + unit test s pozitivním a negativním případem.

### 5.6 Jistota (confidence.py)
- Složené skóre 0–1 z komponent: ověřená citace, shoda s číselníkem, shoda mezi dokumenty, průchod pravidly,
  samohodnocení LLM (nejnižší váha – je nespolehlivé). Výchozí váhy:
  `0.35 quote_verified + 0.30 codelist_match + 0.20 cross_doc_agreement + 0.15 llm_self`,
  při neprošlém pravidle −0.2. Váhy jsou konfigurace, ne konstanty v kódu.
- Pásma: `high` ≥ 0.90, `medium` 0.70–0.89, `low` < 0.70. Prahy se kalibrují na gold standardu (eval/).
- Úroveň automatizace (metodika ÚZIS): A auto, B auto + kontrola, C předvyplnit k potvrzení, D jen upozornit,
  E ručně. Výchozí: high → B, medium → C, low → D, chybí → E. Kódy z volného textu nikdy úroveň A.

### 5.7 API (minimum)
```
GET    /api/patients                      seznam (RČ maskované, pseudonym, stav případu, počet issues)
GET    /api/patients/{key}/documents      dokumenty pacienta
GET    /api/documents/{id}                text po stránkách (pro zvýraznění citací)
POST   /api/documents                     upload (spustí ingest + extrakci, asynchronně)
GET    /api/cases/{id}                    celý NorCase (formát podle schématu)
PATCH  /api/cases/{id}/fields/{field}     editace / potvrzení pole → audit
POST   /api/cases/{id}/export             XML + výsledek validace XSD
GET    /api/metrics                       přesnost, úplnost, opravy, čas (pro dashboard)
```

### 5.8 XML export
- Obálka `ds:dasta` → `ds:is` → `nor:nor` → `nor:nor_dg` (jeden element na případ), atributy = pole.
- Hodnoty převeď na typy z XSD (např. `pohlavi` číslo dle číselníku Pohlavi, `zeme` třímístný kód,
  `htyp` dvoumístné číslo; ne „Z“, „CZE“, „A“ jako v neověřeném ukázkovém XML).
- Validuj proti XSD v `xsd/` (lxml). Export je zablokovaný, dokud existuje `Issue` se `severity: error`
  nebo není případ `approved`.

## 6. LLM – použití a limity

- Endpoint APIM, OpenAI-kompatibilní: `base_url=LLM_BASE_URL`, hlavička `api-key`, model = název deploymentu
  (`LLM_DEPLOYMENT_EXTRACT`). Viz `scripts/test_llm.py`.
- Sdílený rozpočet a rate limity: cache podle `sha256(text) + prompt_version + model` v `data/cache/`;
  souběžnost max 2; `max_retries=2`, žádné smyčky; krátké prompty (posílej relevantní úsek, ne celý dokument).
- Demo pacienti musí jít zobrazit z cache bez jediného volání LLM.
- Poskytovatel LLM je za rozhraním `llm/client.py`, aby šel vyměnit (jiný model, lokální model).

## 7. Frontend – dashboard

Jazyk UI čeština. Obrazovky:
1. **Pacienti:** tabulka (pseudonym, maskované RČ, počet dokumentů, stav případu, počty issues podle závažnosti,
   průměrná jistota). Upload dokumentů.
2. **Případ – formulář NOR:** sekce jako originální formulář (Diagnostická část; Diagnóza; Morfologie; TNM;
   Ostatní; Hlášení). U každého pole: hodnota + název z číselníku, barevné pásmo jistoty, úroveň A–E,
   ikona zdroje. Klik na pole → vpravo zvýrazněná citace v dokumentu. Výběr z číselníku (našeptávač),
   alternativy z jiných faktů, tlačítka Potvrdit / Upravit / Zamítnout.
3. **Dokumenty:** všechny zprávy pacienta, text se zvýrazněnými citacemi všech faktů.
4. **Upozornění:** seznam `issues`, klik přeskočí na pole. Chybějící povinná pole nahoře.
5. **Kvalita:** podíl polí podle pásma jistoty, úplnost povinných polí, počet oprav, čas kontroly
   (z `metrics` a auditu). Na tom ukážeme kritéria poroty.
6. **Export:** náhled XML, výsledek validace XSD, stažení.

Měř čas kontroly: od otevření případu do schválení (aktivní čas), ulož do `metrics.review_seconds`.

## 8. Testovací data a gold standard

- `data/synthetic/`: AZ.pdf, Histologie.pdf, PZ.pdf (Pacient 1, adenokarcinom žaludku). Obsahují záměrné pasti:
  G3 v biopsii vs. Gx v resekátu; cT4aN0M0 vs. ypT3 ypN3b; datum diagnózy jen „3/26“; rozpor v pohlaví
  („poučen“ vs. „pacientka“); topografie „T63 ZALUDEK“ (není MKN-O-3, odvodit C16.3); neplatné RČ.
- `eval/gold/<pacient>.json`: ručně ověřené hodnoty polí. `eval/run_eval.py` počítá po polích přesnost,
  úplnost, správné přiřazení, dohledatelnost (podíl hodnot s ověřenou citací).
- Další syntetické pacienty generuj tak, aby pokrývali: negaci („bez známek metastáz“), suspekci, metastázu
  jako místo odběru, párové orgány (lateralita), více dokumentů s rozpory, sken bez textové vrstvy.

## 9. Pořadí práce

**Řez 1 – frontend nad ukázkou (paralelně s řezem 2):** dashboard čte `examples/pacient1_case.example.json`
(mock endpoint nebo statický import). Obrazovky 1–4, barvy jistoty, zvýraznění citací, editace v paměti.

**Řez 2 – tenký backend end-to-end:** upload 3 PDF Pacienta 1 → text → regex fakty (`dg_nov`, `morfo`,
`t`/`n`/`m`, `pt`/`pn`, `ptnmy`, `pvu`/`ppu`) + LLM pro `grade` a `dat_dg` → resolve → issues → `GET /api/cases/{id}`
vrací JSON validní proti schématu.

**Řez 3 – propojení:** frontend přepnout z ukázky na API, editace přes PATCH + audit.

**Řez 4:** číselníky NOR, výpočet stadia, XML export + XSD, evaluace, metriky, nasazení do Container Apps.

Každý řez končí funkční ukázkou a zeleným `pytest`.

## 10. Role v týmu

1. Extrakce a evaluace (extract/, llm/, eval/).
2. Číselníky, resolve, pravidla, XML (codelists/, resolve/, rules/, export/).
3. Frontend (frontend/).
4. Data, DB, Docker, CI/CD, nasazení, prezentace (data/, db/, Dockerfile, .github/).

## 11. Konvence

- Kód a identifikátory anglicky, UI a zprávy uživateli česky.
- Malé PR do `main`, každý PR s testy. Nepřepisuj cizí modul bez domluvy – měň smlouvu (schéma).
- Před commitem: `pytest`, `ruff check`, `npm run build` (frontend).
- Příkazy:
  ```
  docker compose up --build            # celá aplikace na http://localhost:8000
  cd backend && uvicorn app.main:app --reload
  cd frontend && npm run dev
  pytest
  python eval/run_eval.py
  ```

## 12. Otevřené otázky (neřeš odhadem, zeptej se)

- Přesné kódy číselníků NOR: Lateralita, Grading, Pohlavi, TypPece, StanoveniDg, Onemocneni, KlinickeStadium.
- Formát typu `logical` v DASTA a validní hodnoty `dg_stan` (součet?).
- Balík XSD pro validaci (`xsd/`) – stáhnout z ciselniky.dasta.mzcr.cz.
- Číselníky MKN-O-3 (morfologie, topografie) a TNM 8 – zatím nemáme.
- IRIS: lokálně v Dockeru, nebo hostovaná instance od partnera?
