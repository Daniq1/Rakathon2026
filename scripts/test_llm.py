"""Test připojení k modelům Rakathonu přes APIM (OpenAI-kompatibilní API).

pip install openai python-dotenv
python scripts/test_llm.py
"""
import json
import os

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI(
    base_url=os.environ["LLM_BASE_URL"],
    api_key=os.environ["LLM_API_KEY"],
    # APIM čeká klíč v hlavičce api-key (ne jen v Authorization: Bearer)
    default_headers={"api-key": os.environ["LLM_API_KEY"]},
    max_retries=2,   # žádné nekonečné opakování při 429
    timeout=60,
)
model = os.environ["LLM_DEPLOYMENT_EXTRACT"]

# 1) Prosté volání
r = client.chat.completions.create(
    model=model,
    messages=[{"role": "user", "content": "Ahoj, odpověz jedním slovem."}],
)
print("Odpověď:", r.choices[0].message.content)
print("Tokeny:", r.usage)

# 2) Strukturovaný výstup (JSON) – na tom stojí celá extrakce
text = "Adenoca žaludku, cT4aN0M0. Subtotální resekce žaludku ypT3 ypN3b, LU 24/19."
r = client.chat.completions.create(
    model=model,
    response_format={"type": "json_object"},
    messages=[
        {"role": "system", "content": "Vrať pouze JSON s klíči: t, n, m, y, pt, pn, pvu, ppu. "
                                      "Hodnotu, která v textu není, vrať jako null."},
        {"role": "user", "content": text},
    ],
)
print(json.dumps(json.loads(r.choices[0].message.content), ensure_ascii=False, indent=2))
