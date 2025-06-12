from xml.etree.ElementTree import Element
from datetime import datetime

import dateutil.parser

from .utils import ParseException, ns


class Parser:
    @staticmethod
    def text(root: Element, path: str) -> str:
        text = root.findtext(path, namespaces=ns)
        if text is None:
            raise ParseException(f"No element found at {path}")
        return text

    @staticmethod
    def optional_text(root: Element, path: str) -> str | None:
        return root.findtext(path, namespaces=ns)

    @staticmethod
    def text_list(root: Element, path: str) -> list[str]:
        return [el.text for el in root.findall(path, namespaces=ns) if el.text]

    @staticmethod
    def element_list(root: Element, path: str) -> list[Element]:
        return root.findall(path, namespaces=ns)

    @staticmethod
    def optional_datetime(root: Element, path: str) -> datetime | None:
        element = root.find(path, namespaces=ns)
        if element is None:
            return None
        if element.text is None:
            return None
        return dateutil.parser.parse(element.text)
