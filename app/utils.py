from lxml.etree import _Element
from sippy.utils import LangStr


class ParseException(Exception): ...


class XPathException(Exception): ...


ns = {
    # mets
    "mets": "http://www.loc.gov/METS/",
    "csip": "https://DILCIS.eu/XML/METS/CSIPExtensionMETS",
    "sip": "https://DILCIS.eu/XML/METS/SIPExtensionMETS",
    "xsi": "http://www.w3.org/2001/XMLSchema-instance",
    "xlink": "http://www.w3.org/1999/xlink",
    # descriptive
    "dcterms": "http://purl.org/dc/terms/",
    "xs": "http://www.w3.org/2001/XMLSchema/",
    "edtf": "http://id.loc.gov/datatypes/edtf/",
    "schema": "https://schema.org/",
    # premis
    "premis": "http://www.loc.gov/premis/v3",
    "haObj": "https://data.hetarchief.be/ns/object/",
}


def xpath_element(element: _Element, path: str) -> _Element:
    result = element.xpath(path, namespaces=ns)
    if result is None or len(result) != 1 or not isinstance(result[0], _Element):
        raise XPathException(
            f"Could not resolve '{path}' on {element} to a single element"
        )
    return result[0]


def xpath_element_list(element: _Element, path: str) -> list[_Element]:
    result = element.xpath(path, namespaces=ns)
    if (
        result is None
        or not isinstance(result, list)
        or (len(result) > 0 and not isinstance(result[0], _Element))
    ):
        raise XPathException(
            f"Could not resolve '{path}' on {element} to a list of elements"
        )
    return result


def xpath_text_list(element: _Element, path: str) -> list[str]:
    result = element.xpath(path, namespaces=ns)
    if (
        result is None
        or not isinstance(result, list)
        or (len(result) > 0 and not isinstance(result[0], str))
    ):
        raise XPathException(
            f"Could not resolve '{path}' on {element} to a list of strings"
        )
    return result


def xpath_optional_element(element: _Element, path: str) -> _Element | None:
    result = element.xpath(path, namespaces=ns)
    if result is None or len(result) > 1:
        raise XPathException(
            f"Could not resolve '{path}' on {element} to an optional element"
        )

    return result[0] if len(result) != 0 else None


def xpath_optional_text(element: _Element, path: str) -> str | None:
    result = element.xpath(path, namespaces=ns)
    if (
        result is None
        or len(result) > 1
        or (len(result) > 0 and not isinstance(result[0], str))
    ):
        raise XPathException(
            f"Could not resolve '{path}' on {element} to an optional string"
        )

    return result[0] if len(result) != 0 else None


def xpath_text(element: _Element, path: str) -> str:
    result = element.xpath(path, namespaces=ns)
    if result is None or len(result) != 1 or not isinstance(result[0], str):
        raise XPathException(
            f"Could not resolve '{path}' on {element} to a string. Did you forget 'text()'?"
        )
    return result[0]


def parse_lang_str(element: _Element, path: str) -> LangStr | None:
    elements = xpath_element_list(element, path)

    if len(elements) == 0:
        return None

    kwargs = {}
    for element in elements:
        value = xpath_text(element, "text()")
        lang = xpath_text(element, "@xml:lang")
        kwargs |= {lang: value}

    return LangStr.codes(**kwargs)
