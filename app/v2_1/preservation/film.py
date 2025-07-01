from typing import Self
from xml.etree.ElementTree import Element

from pydantic import BaseModel

from ..utils import Parser


class NumberOfReels(BaseModel):
    value: int

    @classmethod
    def from_xml_tree(cls, element: Element) -> Self:
        if element.text is None:
            raise ValueError()
        return cls(value=int(element.text))


class HasMissingAudioReels(BaseModel):
    value: bool

    @classmethod
    def from_xml_tree(cls, element: Element) -> Self:
        if element.text not in ("true", "false", "0", "1"):
            raise ValueError()
        return cls(value=element.text in ("true", "1"))


class HasMissingImageReels(BaseModel):
    value: bool

    @classmethod
    def from_xml_tree(cls, element: Element) -> Self:
        if element.text not in ("true", "false", "0", "1"):
            raise ValueError()
        return cls(value=element.text in ("true", "1"))


class InLanguage(BaseModel):
    text: str

    @classmethod
    def from_xml_tree(cls, element: Element) -> Self:
        if element.text is None:
            raise ValueError()
        return cls(text=element.text)


class OpenCaptions(BaseModel):
    in_languages: list[InLanguage]

    @classmethod
    def from_xml_tree(cls, element: Element) -> Self:
        langs = Parser.element_list(element, "hasip:inLanguage")
        return cls(in_languages=[InLanguage.from_xml_tree(el) for el in langs])


class HasCaptioning(BaseModel):
    open_captions: list[OpenCaptions]

    @classmethod
    def from_xml_tree(cls, element: Element) -> Self:
        captions = Parser.element_list(element, "hasip:openCaptions")
        return cls(open_captions=[OpenCaptions.from_xml_tree(el) for el in captions])


class ColoringType(BaseModel):
    text: str

    @classmethod
    def from_xml_tree(cls, element: Element) -> Self:
        if element.text is None:
            raise ValueError()
        return cls(text=element.text)


class ImageReel(BaseModel):
    identifier: str
    medium: str
    aspect_ratio: str | None
    material: str | None
    preservation_problems: list[str]
    stock_type: str | None

    coloring_type: list[ColoringType]
    has_captioning: HasCaptioning | None

    @classmethod
    def from_xml_tree(cls, element: Element) -> Self:
        return cls(
            identifier=Parser.text(element, "hasip:identifier"),
            medium=Parser.text(element, "hasip:medium"),
            aspect_ratio=Parser.optional_text(element, "hasip:aspectRatio"),
            material=Parser.optional_text(element, "hasip:material"),
            preservation_problems=Parser.text_list(
                element, "hasip:preservationProblems"
            ),
            stock_type=Parser.optional_text(element, "hasip:stockType"),
            coloring_type=[
                ColoringType.from_xml_tree(coloring_type)
                for coloring_type in Parser.element_list(element, "hasip:coloringType")
            ],
            has_captioning=HasCaptioning.from_xml_tree(captioning)
            if (captioning := Parser.optional_element(element, "hasip:hasCaptioning"))
            else None,
        )


class AudioReel(BaseModel):
    identifier: str
    medium: str
    aspect_ratio: str | None
    material: str | None
    preservation_problems: list[str]
    stock_type: str | None

    @classmethod
    def from_xml_tree(cls, element: Element) -> Self:
        return cls(
            identifier=Parser.text(element, "hasip:identifier"),
            medium=Parser.text(element, "hasip:medium"),
            aspect_ratio=Parser.optional_text(element, "hasip:aspectRatio"),
            material=Parser.optional_text(element, "hasip:material"),
            preservation_problems=Parser.text_list(
                element, "hasip:preservationProblems"
            ),
            stock_type=Parser.optional_text(element, "hasip:stockType"),
        )


class StoredAt(BaseModel):
    image_reels: list[ImageReel]
    audio_reels: list[AudioReel]

    @classmethod
    def from_xml_tree(cls, element: Element) -> Self:
        images = Parser.element_list(element, "hasip:imageReel")
        audios = Parser.element_list(element, "hasip:audioReel")

        return cls(
            image_reels=[ImageReel.from_xml_tree(image) for image in images],
            audio_reels=[AudioReel.from_xml_tree(audio) for audio in audios],
        )


class CarrierSignificantProperties(BaseModel):
    number_of_reels: NumberOfReels | None
    has_missing_audio_reels: HasMissingAudioReels | None
    has_missing_image_reels: HasMissingImageReels | None
    stored_at: list[StoredAt]

    @classmethod
    def from_xml_tree(cls, element: Element) -> Self:
        n_reels = Parser.optional_element(element, "hasip:numberOfReels")
        missing_audio = Parser.optional_element(element, "hasip:hasMissingAudioReels")
        missing_image = Parser.optional_element(element, "hasip:hasMissingImageReels")

        return cls(
            number_of_reels=(NumberOfReels.from_xml_tree(n_reels) if n_reels else None),
            has_missing_audio_reels=(
                HasMissingAudioReels.from_xml_tree(missing_audio)
                if missing_audio
                else None
            ),
            has_missing_image_reels=(
                HasMissingImageReels.from_xml_tree(missing_image)
                if missing_image
                else None
            ),
            stored_at=[
                StoredAt.from_xml_tree(stored_at)
                for stored_at in Parser.element_list(element, "hasip:storedAt")
            ],
        )
