from typing import Any
import xml.etree.ElementTree as ET
from pathlib import Path
from itertools import chain


from pydantic import BaseModel
import pytest

from app.v2_1.descriptive.models.dc_schema import DCPlusSchema, parse_xml
from app.v2_1.namespaces import xsi

sip_examples_paths = Path("tests/sip-examples/2.1").glob("**/dc+schema.xml")
local_examples_path = Path("tests/v2_1/dc_schema/samples").glob("**/*.xml")
dc_schema_paths = chain(sip_examples_paths, local_examples_path)


def _create_set_from_object(object: Any) -> frozenset[Any]:
    object_set = set[Any]()

    if isinstance(object, BaseModel):
        for _, field_value in object.__dict__.items():
            object_set |= _create_set_from_object(field_value)

    elif isinstance(object, (list, tuple, set)):
        for element in object:
            object_set |= _create_set_from_object(element)

    elif object is not None:
        object_set.add(str(object))

    return frozenset(object_set)


def _create_set_from_xml_element(element: ET.Element) -> frozenset[Any]:
    element_set = set[Any]()

    for k, v in element.attrib.items():
        if k != xsi.type:
            element_set.add(v)

    children = [child for child in element]
    for child in children:
        element_set |= _create_set_from_xml_element(child)

    if len(children) == 0:
        element_set.add(element.text)

    return frozenset(element_set)


@pytest.mark.parametrize("path", dc_schema_paths)
def test_examples_completeness(path: Path):
    dc_schema = DCPlusSchema.from_xml(path)
    root_element = parse_xml(path)

    model_set = _create_set_from_object(dc_schema)
    element_set = _create_set_from_xml_element(root_element)

    assert model_set == element_set
