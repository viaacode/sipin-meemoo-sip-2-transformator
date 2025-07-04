from pathlib import Path
from functools import partial

import sippy

from app.v2_1.utils import ParseException

from .models import dc_schema as dcs
from .models.xml_lang import XMLLang


def parse_dc_schema(path: Path) -> partial[sippy.IntellectualEntity]:
    dc_plus_schema = dcs.DCPlusSchema.from_xml(path)
    tf = DCSchemaTransformator(dc_plus_schema)

    return partial(
        sippy.IntellectualEntity,
        name=tf.title,
        alternative_name=tf.alternative,
        duration=tf.extent,
        available=tf.available,
        description=tf.description,
        abstract=tf.abstract,
        date_created=tf.created,
        date_published=tf.issued,
        publisher=tf.publisher,
        creator=tf.creator,
        contributor=tf.contributor,
        spatial=tf.spatial,
        temporal=tf.temporal,
        keywords=tf.subject,
        in_language=tf.in_language,
        license=tf.license,
        copyright_holder=tf.copyright_holder,
        rights=tf.rights,
        type=tf.type,
        format=tf.format,
        height=tf.height,
        width=tf.width,
        depth=tf.depth,
        weight=tf.weight,
        art_medium=tf.art_medium,
        artform=tf.artform,
        schema_is_part_of=tf.schema_is_part_of,
        credit_text=tf.credit_text,
        # Other
        has_part=[],
        is_part_of=[],
        relationship=[],
        genre=[],
        # Bibliographic descriptive metadata
        number_of_pages=None,
        page_number=None,
        issue_number=None,
    )


class DCSchemaTransformator:
    """
    Transforms the dc+schema model to SIP.py objects
    """

    def __init__(self, dc_plus_schema: dcs.DCPlusSchema) -> None:
        self.dc_plus_schema = dc_plus_schema

    @property
    def title(self) -> sippy.LangStr:
        return self.lang_str(self.dc_plus_schema.title)

    @property
    def alternative(self) -> list[sippy.LangStr]:
        if self.dc_plus_schema.alternative is None:
            return []
        return [self.lang_str(self.dc_plus_schema.alternative)]

    @property
    def available(self) -> sippy.DateTime | None:
        if self.dc_plus_schema.available is None:
            return None
        return sippy.DateTime(value=self.dc_plus_schema.available)

    @property
    def description(self) -> sippy.LangStr | None:
        return self.lang_str(self.dc_plus_schema.description)

    @property
    def abstract(self) -> sippy.LangStr | None:
        return self.optional_lang_str(self.dc_plus_schema.abstract)

    @property
    def created(self) -> sippy.EDTF:
        # TODO: check all EDTF levels in transformator
        return sippy.EDTF_level1(value=self.dc_plus_schema.created)

    @property
    def issued(self) -> sippy.EDTF | None:
        if self.dc_plus_schema.issued is None:
            return None
        return sippy.EDTF_level1(value=self.dc_plus_schema.issued)

    @property
    def publisher(self) -> list[sippy.Role]:
        return [self.role(role) for role in self.dc_plus_schema.publisher]

    @property
    def creator(self) -> list[sippy.Role]:
        return [self.role(role) for role in self.dc_plus_schema.creator]

    @property
    def contributor(self) -> list[sippy.Role]:
        return [self.role(role) for role in self.dc_plus_schema.contributor]

    @property
    def spatial(self) -> list[sippy.Place]:
        return [
            sippy.Place(name=sippy.LangStr(nl=s)) for s in self.dc_plus_schema.spatial
        ]

    @property
    def temporal(self) -> list[sippy.LangStr]:
        return [sippy.LangStr(nl=t) for t in self.dc_plus_schema.temporal]

    @property
    def subject(self) -> list[sippy.LangStr]:
        if self.dc_plus_schema.subject is None:
            return []
        return [self.lang_str(self.dc_plus_schema.subject)]

    @property
    def in_language(self) -> list[str]:
        return self.dc_plus_schema.language

    @property
    def license(self) -> list[sippy.Concept | sippy.URIRef[sippy.License]]:
        return [
            sippy.Concept(
                id="https://data.hetarchief.be/id/license/" + license,
                pref_label=sippy.LangStr.codes(nl=license),
            )
            for license in self.dc_plus_schema.license
        ]

    @property
    def copyright_holder(
        self,
    ) -> list[sippy.Thing | sippy.AnyOrganization | sippy.Person]:
        if self.dc_plus_schema.rights_holder is None:
            return []
        return [sippy.Thing(name=self.lang_str(self.dc_plus_schema.rights_holder))]

    @property
    def rights(self) -> list[sippy.LangStr]:
        if self.dc_plus_schema.rights is None:
            return []
        return [self.lang_str(self.dc_plus_schema.rights)]

    @property
    def type(self) -> sippy.EntityClass:
        type = self.dc_plus_schema.type
        type_iri = "haDes:" + type
        entity_classes = [c.value for c in sippy.EntityClass]
        if type_iri not in entity_classes:
            raise ParseException(
                f"dcterms:type must be the local part of one of {entity_classes}"
            )
        return sippy.EntityClass(type_iri)

    @property
    def format(self) -> sippy.String:
        return sippy.String(value=self.dc_plus_schema.format)

    @property
    def height(self) -> sippy.QuantitativeValue | None:
        return self.quantitive_value(self.dc_plus_schema.height)

    @property
    def width(self):
        return self.quantitive_value(self.dc_plus_schema.width)

    @property
    def depth(self):
        return self.quantitive_value(self.dc_plus_schema.depth)

    @property
    def weight(self):
        return self.quantitive_value(self.dc_plus_schema.weight)

    @property
    def art_medium(self) -> list[sippy.LangStr]:
        if self.dc_plus_schema.art_medium is None:
            return []
        return [self.lang_str(self.dc_plus_schema.art_medium)]

    @property
    def artform(self) -> list[sippy.LangStr]:
        if self.dc_plus_schema.artform is None:
            return []
        return [self.lang_str(self.dc_plus_schema.artform)]

    @property
    def schema_is_part_of(self) -> list[sippy.AnyCreativeWork | sippy.BroadcastEvent]:
        return [self.creative_work(cw) for cw in self.dc_plus_schema.is_part_of]

    @property
    def credit_text(self) -> list[sippy.LangStr]:
        return [sippy.LangStr(nl=s) for s in self.dc_plus_schema.credit_text]

    @property
    def extent(self) -> sippy.Duration | None:
        if self.dc_plus_schema.extent is None:
            return None
        return sippy.Duration(value=self.dc_plus_schema.extent)

    def optional_lang_str(self, str: XMLLang | None) -> sippy.LangStr | None:
        if str is None:
            return None
        return sippy.LangStr.codes(**str.content)

    def lang_str(self, str: XMLLang) -> sippy.LangStr:
        return sippy.LangStr.codes(**str.content)

    def role(self, role: dcs.Creator | dcs.Publisher | dcs.Contributor) -> sippy.Role:
        is_person = role.birth_date or role.death_date
        if is_person:
            member = sippy.Person(
                name=self.lang_str(role.name),
                birth_date=(
                    sippy.EDTF_level1(value=role.birth_date)
                    if role.birth_date
                    else None
                ),
                death_date=(
                    sippy.EDTF_level1(value=role.death_date)
                    if role.death_date
                    else None
                ),
            )
        else:
            member = sippy.Thing(name=self.lang_str(role.name))

        match role:
            case dcs.Contributor():
                default_role_name = "Bijdrager"
            case dcs.Publisher():
                default_role_name = "Publisher"
            case dcs.Creator():
                default_role_name = "Maker"
            case _:
                raise AssertionError(
                    "Role should be creator, publisher or contributor."
                )
        role_name = role.role_name if role.role_name else default_role_name

        return sippy.Role(
            role_name=role_name,
            creator=member if isinstance(role, dcs.Creator) else None,
            publisher=member if isinstance(role, dcs.Publisher) else None,
            contributor=member if isinstance(role, dcs.Contributor) else None,
            name=sippy.LangStr.codes(nl=role_name),
        )

    def quantitive_value(
        self, measurement: dcs._Measurement | None
    ) -> sippy.QuantitativeValue | None:
        if measurement is None:
            return None

        match measurement.unit_text:
            case "mm":
                unit_code = "MMT"
            case "cm":
                unit_code = "CMT"
            case "m":
                unit_code = "MTR"
            case "kg":
                unit_code = "KGM"

        return sippy.QuantitativeValue(
            value=sippy.Float(value=measurement.value),
            unit_text=measurement.unit_text,
            unit_code=unit_code,
        )

    def creative_work(
        self, sip_creative_work: dcs.AnyCreativeWork | dcs.BroadcastEvent
    ) -> sippy.AnyCreativeWork | sippy.BroadcastEvent:
        name = self.lang_str(sip_creative_work.name)
        match sip_creative_work:
            case dcs.BroadcastEvent():
                # TODO: must first be added to datamodels properly
                return sippy.BroadcastEvent(name=name)
            case dcs.Episode():
                # TODO: hardcoded identifier
                return sippy.Episode(name=name)
            case dcs.ArchiveComponent():
                return sippy.ArchiveComponent(name=name)
            case dcs.CreativeWorkSeries():
                return sippy.CreativeWorkSeries(name=name)
            case dcs.CreativeWorkSeason():
                return sippy.CreativeWorkSeason(name=name)
