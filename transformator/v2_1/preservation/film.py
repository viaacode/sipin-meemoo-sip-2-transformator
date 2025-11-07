from typing import Self

from pydantic.dataclasses import dataclass

from eark_models.namespaces import Namespace, schema
from eark_models.etree import _Element
from eark_models.langstring import UniqueLang, unique_lang

from ..utils import TransformatorError


class haSip(Namespace):
    __ns__ = "https://data.hetarchief.be/ns/sip/"


@dataclass
class OpenCaptions:
    in_languages: list[str]

    @classmethod
    def from_xml_tree(cls, element: _Element) -> Self:
        langs = [el.text for el in element.findall(haSip.inLanguage) if el.text]
        return cls(in_languages=langs)


@dataclass
class HasCaptioning:
    open_captions: list[OpenCaptions]

    @classmethod
    def from_xml_tree(cls, element: _Element) -> Self:
        captions = element.findall(haSip.openCaptions)
        return cls(open_captions=[OpenCaptions.from_xml_tree(el) for el in captions])


@dataclass
class Brand:
    name: UniqueLang

    @classmethod
    def from_xml_tree(cls, element: _Element) -> Self:
        return cls(name=unique_lang(element, haSip.name))


@dataclass
class StorageLocationValue:
    value: str

    @classmethod
    def from_xml_tree(cls, element: _Element) -> Self:
        return cls(
            value=element.text if element.text else "",
        )


@dataclass
class PhysicalCarrier:
    identifier: str
    medium: str
    preservation_problems: list[str]
    brand: Brand | None
    storage_location_value: StorageLocationValue | None
    material: str | None

    @classmethod
    def from_xml_tree(cls, element: _Element) -> Self:
        brand = (
            Brand.from_xml_tree(brand) if (brand := element.find(haSip.brand)) else None
        )
        storage_location_value = (
            StorageLocationValue.from_xml_tree(value)
            if (value := element.find(haSip.value))
            else None
        )
        return cls(
            identifier=get_text(element, haSip.identifier),
            material=element.findtext(haSip.material),
            medium=get_text(element, haSip.medium),
            preservation_problems=[
                (el.text if el.text else "")
                for el in element.findall(haSip.preservationProblems)
            ],
            brand=brand,
            storage_location_value=storage_location_value,
        )


@dataclass
class ImageReel(PhysicalCarrier):
    aspect_ratio: str | None
    stock_type: str | None
    coloring_type: list[str]
    has_captioning: HasCaptioning | None

    @classmethod
    def from_xml_tree(cls, element: _Element) -> Self:
        captioning = element.find(haSip.hasCaptioning)
        brand = (
            Brand.from_xml_tree(brand) if (brand := element.find(haSip.brand)) else None
        )
        storage_location_value = (
            StorageLocationValue.from_xml_tree(value)
            if (value := element.find(haSip.value))
            else None
        )
        return cls(
            material=element.findtext(haSip.material),
            identifier=get_text(element, haSip.identifier),
            medium=get_text(element, haSip.medium),
            aspect_ratio=element.findtext(haSip.aspectRatio),
            preservation_problems=[
                (el.text if el.text else "")
                for el in element.findall(haSip.preservationProblems)
            ],
            stock_type=element.findtext(haSip.stockType),
            coloring_type=[
                (el.text if el.text else "")
                for el in element.findall(haSip.coloringType)
            ],
            has_captioning=(
                HasCaptioning.from_xml_tree(captioning)
                if captioning is not None
                else None
            ),
            brand=brand,
            storage_location_value=storage_location_value,
        )


@dataclass(kw_only=True)
class AudioReel(PhysicalCarrier):
    aspect_ratio: str | None
    stock_type: str | None

    @classmethod
    def from_xml_tree(cls, element: _Element) -> Self:
        brand = (
            Brand.from_xml_tree(brand) if (brand := element.find(haSip.brand)) else None
        )
        storage_location_value = (
            StorageLocationValue.from_xml_tree(value)
            if (value := element.find(haSip.value))
            else None
        )
        return cls(
            identifier=get_text(element, haSip.identifier),
            medium=get_text(element, haSip.medium),
            aspect_ratio=element.findtext(haSip.aspectRatio),
            material=element.findtext(haSip.material),
            preservation_problems=[
                (el.text if el.text else "")
                for el in element.findall(haSip.preservationProblems)
            ],
            stock_type=element.findtext(haSip.stockType),
            brand=brand,
            storage_location_value=storage_location_value,
        )


@dataclass(kw_only=True)
class StoredAt:
    physical_carriers: list[PhysicalCarrier]
    image_reels: list[ImageReel]
    audio_reels: list[AudioReel]

    @classmethod
    def from_xml_tree(cls, element: _Element) -> Self:
        carriers = element.findall(haSip.physicalCarrier)
        images = element.findall(haSip.imageReel)
        audios = element.findall(haSip.audioReel)

        return cls(
            physical_carriers=[PhysicalCarrier.from_xml_tree(car) for car in carriers],
            image_reels=[ImageReel.from_xml_tree(image) for image in images],
            audio_reels=[AudioReel.from_xml_tree(audio) for audio in audios],
        )


@dataclass(kw_only=True)
class CarrierSignificantProperties:
    number_of_reels: int | None
    has_missing_audio_reels: bool | None
    has_missing_image_reels: bool | None
    stored_at: list[StoredAt]

    @classmethod
    def from_xml_tree(cls, element: _Element) -> Self:
        n_reels = element.findtext(haSip.numberOfReels)
        missing_audio = element.findtext(haSip.hasMissingAudioReels)
        missing_image = element.findtext(haSip.hasMissingImageReels)

        return cls(
            number_of_reels=int(n_reels) if n_reels is not None else None,
            has_missing_audio_reels=(
                bool(missing_audio) if missing_audio is not None else None
            ),
            has_missing_image_reels=(
                bool(missing_image) if missing_image is not None else None
            ),
            stored_at=[
                StoredAt.from_xml_tree(stored_at)
                for stored_at in element.findall(haSip.storedAt)
            ],
        )


def get_text(element: _Element, path: str) -> str:
    el = element.find(path)
    if el is None:
        raise TransformatorError(f"No element found at {path}")
    return el.text if el.text is not None else ""
