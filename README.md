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
