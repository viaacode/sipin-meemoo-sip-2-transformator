from typing import Any
from itertools import chain
from pathlib import Path

from eark_models import mods
import sippy

from app.utils import ParseException


def parse_mods(path: Path) -> dict[str, Any]:
    desc = mods.MODS.from_xml(path)

    main_title_info = next(info for info in desc.titleInfos if info.type is None)
    main_title = next(iter(main_title_info.titles))

    date_created = next(chain(*[info.datesCreated for info in desc.originInfos]))
    if date_created.date.encoding != "edtf":
        raise ParseException(
            "Date created must have attribute 'encoding' set to 'edtf'"
        )

    return {
        "name": sippy.LangStr(nl=main_title.value),
        "date_created": sippy.EDTF_level1(value=date_created.date.value),
        "format": sippy.String(value="newspaper"),
    }
