from app.v2_1 import transform_sip
import sippy


def test_basic():
    data = transform_sip(
        "tests/sip-examples/2.1/basic_deec5d89-3024-4cbd-afcd-e18af4ad33ec/uuid-de61d4af-d19c-4cc7-864d-55573875b438"
    )
    sippy.SIP.deserialize(data)


def test_film():
    data = transform_sip(
        "tests/sip-examples/2.1/film_standard_mkv/uuid-2746e598-75cd-47b5-9a3e-8df18e98bb95"
    )
    sippy.SIP.deserialize(data)


def test_material_artwork_2d():
    data = transform_sip(
        "tests/sip-examples/2.1/2D_fa307608-35c3-11ed-9243-7e92631d7d27/uuid-de61d4af-d19c-4cc7-864d-55573875b438"
    )
    sippy.SIP.deserialize(data)


def test_material_artwork_3d():
    data = transform_sip(
        "tests/sip-examples/2.1/3D_3d4bd7ca-38c6-11ed-95f2-7e92631d7d28/uuid-de61d4af-d19c-4cc7-864d-55573875b438"
    )
    sippy.SIP.deserialize(data)


# Implementation of the bibliographic profile was pushed back
# def test_newspaper():
#     transform_sip(
#         "tests/sip-examples/2.1/newspaper_c44a0b0d-6e2f-4af2-9dab-3a9d447288d0/uuid-c44a0b0d-6e2f-4af2-9dab-3a9d447288d0"
#     )


# def test_newspaper_tiff():
#     transform_sip(
#         "tests/sip-examples/2.1/newspaper_tiff_alto_pdf_ebe47259-8f23-4a2d-bf49-55ae1d855393/uuid-ebe47259-8f23-4a2d-bf49-55ae1d855393"
#     )
