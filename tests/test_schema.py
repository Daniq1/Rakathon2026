import json

import jsonschema

from conftest import REPO


def test_example_is_valid(schema):
    example = json.loads((REPO / "examples" / "pacient1_case.example.json").read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator.check_schema(schema)
    jsonschema.Draft202012Validator(schema).validate(example)


def test_pydantic_models_accept_example():
    from app.models import CaseBundle

    example = json.loads((REPO / "examples" / "pacient1_case.example.json").read_text(encoding="utf-8"))
    bundle = CaseBundle.model_validate(example)
    assert bundle.case.fields["grade"].status == "conflict"


def test_model_field_names_match_schema(schema):
    from typing import get_args

    from app.models import NorFieldName

    assert set(get_args(NorFieldName)) == set(schema["$defs"]["NorFieldName"]["enum"])
