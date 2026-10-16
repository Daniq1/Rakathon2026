from datetime import date

from app.ingest.doctype import detect_doc_type
from app.ingest.pseudonymize import pseudonymize
from app.ingest.rc import find_rc, validate


# Syntetická RČ dělitelná 11 (žádné reálné osoby)
def test_rc_valid_female():
    info = validate("736028/0004")  # měsíc 60 → žena, říjen
    assert info.valid
    assert info.sex == "F"
    assert info.birth_date == date(1973, 10, 28)


def test_rc_valid_male_and_female():
    assert validate("800101/0006").sex == "M"
    assert validate("805101/0000").sex == "F"


def test_rc_not_divisible_by_11():
    assert not validate("800101/0007").valid


def test_rc_invalid_anonymized():
    info = validate("123456/1111")
    assert not info.valid
    assert info.errors


def test_rc_invalid_length():
    assert not validate("12345").valid


def test_find_rc_in_header():
    assert find_rc("Pacient 1 r.č. 123456/1111 poj.\ntel.") == "123456/1111"
    assert find_rc("Pacient 1 Dat. nar.: Č. poj.:\nbez rč") is None


def test_doc_types():
    assert detect_doc_type("Pacient 1 r.č. 1/1\ntel.\nPropouštěcí zpráva\n") == "propoustejici_zprava"
    assert detect_doc_type("Pacient\nAmbulantní zpráva\n") == "ambulantni_zprava"
    assert detect_doc_type("Laboratorní vyšetření\nPacient 1\nHistologie\nB_AA") == "histologie"
    assert detect_doc_type("Pacient 4\nMamologie - MDT\n") == "jine"
    assert detect_doc_type("nic\n") == "nezname"


def test_pseudonymize_removes_identifiers():
    text = (
        "Jan Novák r.č. 800101/0006 poj.\nAdresa: Hlavní 1, Ostrava tel. 603 123 456\n"
        "Dat. nar.: 1.1.1980\nadenoCa G3"
    )
    out = pseudonymize(text, "Pacient 7")
    assert "Novák" not in out and "800101" not in out and "603" not in out and "Hlavní" not in out
    assert "1.1.1980" not in out
    assert out.startswith("Pacient 7 r.č. [RC]")
    assert "adenoCa G3" in out
