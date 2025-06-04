from typing import Self
from xml.etree.ElementTree import Element

from pydantic import BaseModel

from app.utils import ParseException, ns


class LangStr(BaseModel):
    content: dict[str, str]

    @classmethod
    def new(cls, root: Element, path: str) -> Self:
        lang_str = cls.optional(root, path)
        if lang_str is None:
            raise ParseException(f"Cannot create lang string from elements at {path}")
        return lang_str

    @classmethod
    def optional(cls, root: Element, path: str) -> Self | None:
        elements = root.findall(path, namespaces=ns)
        if len(elements) == 0:
            return None

        content = {}
        for element in elements:
            value = element.text
            lang = element.get("{http://www.w3.org/XML/1998/namespace}lang")
            if lang is None:
                raise ParseException(
                    f"No `xml:lang` attribute found on lang string {path}."
                )
            content |= {lang: value}
        return cls(content=content)
