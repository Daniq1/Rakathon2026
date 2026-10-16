# AI NOR – startovní balík (Rakathon 2026, tým 4)

| Soubor | K čemu |
| --- | --- |
| `.env.example` | Šablona proměnných; zkopírovat na `.env` (v `.gitignore`) |
| `scripts/test_llm.sh` | Testovací volání curlem |
| `scripts/test_llm.py` | Totéž z Pythonu + test JSON výstupu |
| `schema/nor_case.schema.json` | Interní model = smlouva mezi moduly (návrh 0.1.0) |
| `examples/pacient1_case.example.json` | Ukázková instance pro Pacienta 1 (validní vůči schématu) |
| `hello/` | Hello world FastAPI + Dockerfile |
| `scripts/deploy_hello.sh` | Nasazení do Azure Container Apps (rg-teamNN) |
| `.github/workflows/build-image.yml` | Build image do GHCR |

Validace příkladu: `pip install jsonschema && python -c "import json,jsonschema;jsonschema.validate(json.load(open('examples/pacient1_case.example.json')),json.load(open('schema/nor_case.schema.json')))"`

## Backend (řez 2)

```bash
python -m venv .venv && .venv/Scripts/pip install -r backend/requirements.txt   # Linux/macOS: .venv/bin/pip
cd backend && ../.venv/Scripts/python -m uvicorn app.main:app --reload            # http://localhost:8000
pytest                                                                             # z kořene repa
ruff check .
```

Upload a výsledek:

```bash
curl -F files=@AZ.pdf -F files=@Histologie.pdf -F files=@PZ.pdf "localhost:8000/api/documents?sync=true"
curl localhost:8000/api/patients                     # case_id
curl localhost:8000/api/cases/<case_id>              # NorCase podle schema/nor_case.schema.json
```

- Bez `sync=true` běží extrakce na pozadí (`documents_processing` v `/api/patients`).
- Dokumenty bez RČ v hlavičce (např. histologie) se přiřadí k jedinému RČ v dávce nebo podle pole `patient_key`.
- LLM (grade, dat_dg) dostává jen pseudonymizované úryvky. Odpovědi se cachují v `data/cache/` (gitignore);
  demo cache pro Pacienta 1 je v `data/demo_cache/`, takže demo i testy běží bez volání LLM.
- Váhy jistoty: `backend/config/confidence.json`, administrativní pole pracoviště: `backend/config/workplace.json`.
- Číselníky: `data/codelists/README.md` (grading je zatím provizorní).
