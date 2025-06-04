from app.app import parse_sip


def test_film():
    parse_sip(
        "tests/sip-examples/2.1/film_standard_mkv/uuid-2746e598-75cd-47b5-9a3e-8df18e98bb95"
    )


def test_newspaper():
    parse_sip(
        "tests/sip-examples/2.1/newspaper_c44a0b0d-6e2f-4af2-9dab-3a9d447288d0/uuid-c44a0b0d-6e2f-4af2-9dab-3a9d447288d0"
    )
