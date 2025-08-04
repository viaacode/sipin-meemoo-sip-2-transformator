from pathlib import Path
import pytest

import sippy
from app.v2_1 import transform_sip

sip_paths = set(Path("tests/sip-examples/2.1").iterdir())

exclude = [
    "tests/sip-examples/2.1/ftp_sidecar_904c6e86-d36a-4630-897b-bb560ce4b690",
    "tests/sip-examples/2.1/newspaper_tiff_alto_pdf_ebe47259-8f23-4a2d-bf49-55ae1d855393",
    "tests/sip-examples/2.1/newspaper_c44a0b0d-6e2f-4af2-9dab-3a9d447288d0",
    "tests/sip-examples/2.1/subtitles_d3e1a978-3dd8-4b46-9314-d9189a1c94c6",
]

excluded_paths = {Path(p) for p in exclude}

sip_paths = sip_paths - excluded_paths
unzipped_paths = [(next(path.iterdir())) for path in sip_paths]
unzipped_path_names = [str(path.parent.name) for path in unzipped_paths]


@pytest.mark.parametrize("unzipped_path", unzipped_paths, ids=unzipped_path_names)
def test_examples(unzipped_path: Path):
    data = transform_sip(str(unzipped_path))
    sippy.SIP.deserialize(data)
