from io import StringIO

import pytest

from app.v2_1.utils import ParseException
from app.v2_1.descriptive.models import dc_schema, xml_lang
from app.v2_1.descriptive.models.dc_schema import parse_is_part_of, parse_xml


def test_parsing_with_default_namespace():
    content = r"""<schema:isPartOf xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:schema="https://schema.org/" xsi:type="schema:Episode">
        <schema:name xml:lang="en">SIP.py, the SIP model</schema:name></schema:isPartOf>"""

    file = StringIO(content)
    root = parse_xml(file)
    parse_is_part_of(root)


def test_episode():
    content = """<schema:isPartOf  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:schema="https://schema.org/"
      xsi:type="schema:Episode">
      <schema:name xml:lang="en">SIP.py, the SIP model</schema:name>
    </schema:isPartOf>
    """

    file = StringIO(content)
    root = parse_xml(file)
    episode = parse_is_part_of(root)

    assert episode == dc_schema.Episode(
        name=xml_lang.XMLLang(
            entries=[
                xml_lang.Entry(lang="en", value="SIP.py, the SIP model"),
            ]
        )
    )


def test_broadcast_event():
    content = """<myschema:isPartOf  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:myschema="https://schema.org/"
      xsi:type="myschema:BroadcastEvent">
      <myschema:name xml:lang="fr">Eventfully</myschema:name>
    </myschema:isPartOf>
    """

    file = StringIO(content)
    root = parse_xml(file)
    episode = parse_is_part_of(root)

    assert episode == dc_schema.BroadcastEvent(
        name=xml_lang.XMLLang(
            entries=[
                xml_lang.Entry(lang="fr", value="Eventfully"),
            ]
        )
    )


def test_parsing_with_non_default_namespace():
    content = """<myschema:isPartOf xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:myschema="https://schema.org/"
      xsi:type="myschema:BroadcastEvent">
      <myschema:name xml:lang="fr">Eventfully</myschema:name>
    </myschema:isPartOf>
    """

    file = StringIO(content)
    root = parse_xml(file)
    _ = parse_is_part_of(root)


def test_parsing_without_xsi_type():
    content = """<schema:isPartOf xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:schema="https://schema.org/">
      <schema:name xml:lang="en">SIP.py, the SIP model</schema:name>
    </schema:isPartOf>
    """

    file = StringIO(content)
    root = parse_xml(file)

    with pytest.raises(ParseException):
        _ = parse_is_part_of(root)


def test_parsing_with_empty_xsi_type():
    content = """<schema:isPartOf xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:schema="https://schema.org/"
        xsi:type="">
      <schema:name xml:lang="en">SIP.py, the SIP model</schema:name>
    </schema:isPartOf>
    """

    file = StringIO(content)
    root = parse_xml(file)

    with pytest.raises(ParseException):
        _ = parse_is_part_of(root)


def test_has_parts_inside_is_part_of():
    content = """<schema:isPartOf xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:schema="https://schema.org/"
        xsi:type="schema:CreativeWorkSeries">
      <schema:name xml:lang="en">my creative work series</schema:name>
      <schema:hasPart>
          <schema:name xml:lang="nl">has part</schema:name>
      </schema:hasPart>
      <schema:hasPart>
          <schema:name xml:lang="nl">has part 2</schema:name>
      </schema:hasPart>
    </schema:isPartOf>
    """

    file = StringIO(content)
    root = parse_xml(file)
    _ = parse_is_part_of(root)
