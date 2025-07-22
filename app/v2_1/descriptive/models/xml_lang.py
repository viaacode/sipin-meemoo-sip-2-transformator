from typing import Self
from xml.etree.ElementTree import Element

from pydantic import BaseModel

import sippy

from ...utils import ParseException, ns


class Entry(BaseModel):
    lang: str
    value: str


class XMLLang(BaseModel):
    entries: list[Entry]

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

        entries = []
        for element in elements:
            value = element.text
            if value is None:
                value = ""
            lang = element.get("{http://www.w3.org/XML/1998/namespace}lang")
            if lang is None:
                raise ParseException(
                    f"No `xml:lang` attribute found on lang string {path}."
                )
            entries.append(Entry(lang=lang, value=value))
        return cls(entries=entries)

    def _to_lang_string(self) -> list[sippy.LangString]:
        return [
            sippy.LangString(lang=entry.lang, value=entry.value)
            for entry in self.entries
        ]

    def to_lang_strings(self) -> sippy.LangStrings:
        return sippy.LangStrings(root=self._to_lang_string())

    def to_unique_lang_strings(self) -> sippy.UniqueLangStrings:
        return sippy.UniqueLangStrings(root=self._to_lang_string())
