from app.v2_1 import parse_sip


def test_basic():
    parse_sip(
        "tests/sip-examples/2.1/basic_deec5d89-3024-4cbd-afcd-e18af4ad33ec/uuid-de61d4af-d19c-4cc7-864d-55573875b438"
    )


def test_film():
    parse_sip(
        "tests/sip-examples/2.1/film_standard_mkv/uuid-2746e598-75cd-47b5-9a3e-8df18e98bb95"
    )


def test_newspaper():
    parse_sip(
        "tests/sip-examples/2.1/newspaper_c44a0b0d-6e2f-4af2-9dab-3a9d447288d0/uuid-c44a0b0d-6e2f-4af2-9dab-3a9d447288d0"
    )


def test_newspaper_tiff():
    parse_sip(
        "tests/sip-examples/2.1/newspaper_tiff_alto_pdf_ebe47259-8f23-4a2d-bf49-55ae1d855393/uuid-ebe47259-8f23-4a2d-bf49-55ae1d855393"
    )
