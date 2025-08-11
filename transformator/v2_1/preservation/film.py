from typing import Self
from xml.etree.ElementTree import Element

from pydantic.dataclasses import dataclass

from eark_models.namespaces import Namespace

from ..utils import TransformatorError


class haSip(Namespace):
    __ns__ = "https://data.hetarchief.be/ns/sip/"


@dataclass
class OpenCaptions:
    in_languages: list[str]

    @classmethod
    def from_xml_tree(cls, element: Element) -> Self:
        langs = [el.text for el in element.findall(haSip.inLanguage) if el.text]
        return cls(in_languages=langs)


@dataclass
class HasCaptioning:
    open_captions: list[OpenCaptions]

    @classmethod
    def from_xml_tree(cls, element: Element) -> Self:
        captions = element.findall(haSip.openCaptions)
        return cls(open_captions=[OpenCaptions.from_xml_tree(el) for el in captions])


@dataclass
class ImageReel:
    identifier: str
    medium: str
    aspect_ratio: str | None
    material: str | None
    preservation_problems: list[str]
    stock_type: str | None

    coloring_type: list[str]
    has_captioning: HasCaptioning | None

    @classmethod
    def from_xml_tree(cls, element: Element) -> Self:
        captioning = element.find(haSip.hasCaptioning)
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
            coloring_type=[
                (el.text if el.text else "")
                for el in element.findall(haSip.coloringType)
            ],
            has_captioning=(
                HasCaptioning.from_xml_tree(captioning)
                if captioning is not None
                else None
            ),
        )


@dataclass(kw_only=True)
class AudioReel:
    identifier: str
    medium: str
    aspect_ratio: str | None
    material: str | None
    preservation_problems: list[str]
    stock_type: str | None

    @classmethod
    def from_xml_tree(cls, element: Element) -> Self:
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
        )


@dataclass(kw_only=True)
class StoredAt:
    image_reels: list[ImageReel]
    audio_reels: list[AudioReel]

    @classmethod
    def from_xml_tree(cls, element: Element) -> Self:
        images = element.findall(haSip.imageReel)
        audios = element.findall(haSip.audioReel)

        return cls(
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
    def from_xml_tree(cls, element: Element) -> Self:
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


def get_text(element: Element, path: str) -> str:
    el = element.find(path)
    if el is None:
        raise TransformatorError(f"No element found at {path}")
    return el.text if el.text is not None else ""
