from typing import Self
from pathlib import Path
from functools import partial

from pydantic.dataclasses import dataclass

from .models import mets, premis
from .utils import ParseException


@dataclass
class Level:
    """
    Represents all metadata information at a certain SIP structure level, eiher the package level or representaiton level.

    The relative path is the path from the root of the SIP -- including the name of the SIP itself -- to the root of the level.
    """

    relative_path: Path
    mets_info: mets.METS
    premis_info: premis.Premis

    @classmethod
    def partial(cls, path: Path) -> partial[Self]:
        mets_info = mets.parse_mets(path)
        return partial(
            cls,
            mets_info=mets_info,
            premis_info=Level.parse_premis(mets_info),
        )

    @classmethod
    def package(cls, path: Path) -> Self:
        package_level = cls.partial(path)
        return package_level(relative_path=path.parent)

    @classmethod
    def representation(cls, path: Path) -> Self:
        representation_level = cls.partial(path)
        package_path = path.parent.parent
        return representation_level(relative_path=package_path.parent)

    @staticmethod
    def parse_premis(mets_model: mets.METS) -> premis.Premis:
        if mets_model.administrative_metadata is None:
            raise ParseException("No PREMIS found.")
        return premis.Premis.from_xml(mets_model.administrative_metadata)
