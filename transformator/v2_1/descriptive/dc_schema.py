from pathlib import Path
from functools import partial

from pydantic.dataclasses import dataclass

import sippy

from ..utils import TransformatorError
from ..models import dcs


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
        genre=tf.genre,
        # Bibliographic descriptive metadata
        number_of_pages=None,
        page_number=None,
        issue_number=None,
    )


@dataclass
class DCSchemaTransformator:
    """
    Transforms the dc+schema model to SIP.py objects
    """

    dc_plus_schema: dcs.DCPlusSchema

    @property
    def title(self) -> sippy.UniqueLangStrings:
        return to_unique_lang_strings(self.dc_plus_schema.title)

    @property
    def alternative(self) -> sippy.LangStrings | None:
        if len(self.dc_plus_schema.alternative) == 0:
            return None
        return to_lang_strings(self.dc_plus_schema.alternative)

    @property
    def available(self) -> sippy.DateTime | None:
        if self.dc_plus_schema.available is None:
            return None
        return sippy.DateTime(value=self.dc_plus_schema.available)

    @property
    def description(self) -> sippy.UniqueLangStrings | None:
        return to_unique_lang_strings(self.dc_plus_schema.description)

    @property
    def abstract(self) -> sippy.UniqueLangStrings | None:
        if len(self.dc_plus_schema.abstract) == 0:
            return None
        return to_unique_lang_strings(self.dc_plus_schema.abstract)

    @property
    def created(self) -> sippy.EDTF:
        # TODO: check all EDTF levels in transformator
        return to_sippy_edtf(self.dc_plus_schema.created)

    @property
    def issued(self) -> sippy.EDTF | None:
        if self.dc_plus_schema.issued is None:
            return None
        return to_sippy_edtf(self.dc_plus_schema.issued)

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
            sippy.Place(name=sippy.UniqueLangStrings.codes(nl=s))
            for s in self.dc_plus_schema.spatial
        ]

    @property
    def temporal(self) -> sippy.LangStrings | None:
        if len(self.dc_plus_schema.temporal) == 0:
            return None
        return to_lang_strings(self.dc_plus_schema.temporal)

    @property
    def subject(self) -> sippy.LangStrings | None:
        if len(self.dc_plus_schema.subject) == 0:
            return None
        return to_lang_strings(self.dc_plus_schema.subject)

    @property
    def in_language(self) -> list[str]:
        return self.dc_plus_schema.language

    @property
    def license(self) -> list[sippy.Concept | sippy.URIRef[sippy.License]]:
        return [
            sippy.Concept(
                id="https://data.hetarchief.be/id/license/" + license,
                pref_label=sippy.UniqueLangStrings.codes(nl=license),
            )
            for license in self.dc_plus_schema.license
        ]

    @property
    def copyright_holder(
        self,
    ) -> list[sippy.Thing | sippy.AnyOrganization | sippy.Person]:
        if len(self.dc_plus_schema.rights_holder) == 0:
            return []
        return [
            sippy.Thing(name=to_unique_lang_strings(self.dc_plus_schema.rights_holder))
        ]

    @property
    def rights(self) -> sippy.LangStrings | None:
        if len(self.dc_plus_schema.rights) == 0:
            return None
        return to_lang_strings(self.dc_plus_schema.rights)

    @property
    def type(self) -> sippy.EntityClass:
        type = self.dc_plus_schema.type
        type_iri = "haDes:" + type
        entity_classes = [c.value for c in sippy.EntityClass]
        if type_iri not in entity_classes:
            raise TransformatorError(
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
    def art_medium(self) -> sippy.LangStrings | None:
        if len(self.dc_plus_schema.art_medium) == 0:
            return None
        return to_lang_strings(self.dc_plus_schema.art_medium)

    @property
    def artform(self) -> sippy.LangStrings | None:
        if len(self.dc_plus_schema.artform) == 0:
            return None
        return to_lang_strings(self.dc_plus_schema.artform)

    @property
    def schema_is_part_of(self) -> list[sippy.AnyCreativeWork | sippy.BroadcastEvent]:
        return [self.creative_work(cw) for cw in self.dc_plus_schema.is_part_of]

    @property
    def credit_text(self) -> sippy.LangStrings | None:
        if len(self.dc_plus_schema.credit_text) == 0:
            return None
        return to_lang_strings(self.dc_plus_schema.credit_text)

    @property
    def extent(self) -> sippy.Duration | None:
        if self.dc_plus_schema.extent is None:
            return None
        return sippy.Duration(value=self.dc_plus_schema.extent)

    def role(self, role: dcs.Creator | dcs.Publisher | dcs.Contributor) -> sippy.Role:
        is_person = role.birth_date or role.death_date
        if is_person:
            member = sippy.Person(
                name=to_unique_lang_strings(role.name),
                birth_date=(
                    sippy.EDTF_level1(value=role.birth_date.text)
                    if role.birth_date
                    else None
                ),
                death_date=(
                    sippy.EDTF_level1(value=role.death_date.text)
                    if role.death_date
                    else None
                ),
            )
        else:
            member = sippy.Thing(name=to_unique_lang_strings(role.name))

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
            name=sippy.UniqueLangStrings.codes(nl=role_name),
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
            value=sippy.Float(value=float(measurement.value)),
            unit_text=measurement.unit_text,
            unit_code=unit_code,
            name=sippy.UniqueLangStrings.codes(nl="Quantitative Value"),
        )

    def creative_work(
        self, sip_creative_work: dcs.AnyCreativeWork | dcs.BroadcastEvent
    ) -> sippy.AnyCreativeWork | sippy.BroadcastEvent:
        name = to_unique_lang_strings(sip_creative_work.name)
        match sip_creative_work:
            case dcs.BroadcastEvent():
                return sippy.BroadcastEvent(name=name)
            case dcs.Episode():
                # TODO: identifier in datamodels is 1..1
                return sippy.Episode(name=name)
            case dcs.ArchiveComponent():
                return sippy.ArchiveComponent(name=name)
            case dcs.CreativeWorkSeries():
                has_part_names = [
                    to_unique_lang_strings(has_part.name)
                    for has_part in sip_creative_work.has_part
                ]
                return sippy.CreativeWorkSeries(
                    name=name,
                    position=sip_creative_work.position,
                    has_part=[
                        sippy.CreativeWorkSeries(
                            name=has_part_name,
                            position=None,
                            has_part=[],
                        )
                        for has_part_name in has_part_names
                    ],
                )
            case dcs.CreativeWorkSeason():
                return sippy.CreativeWorkSeason(
                    name=name,
                    season_number=sip_creative_work.season_number,
                )

    @property
    def genre(self) -> sippy.UniqueLangStrings | None:
        if len(self.dc_plus_schema.genre) == 0:
            return None
        return to_unique_lang_strings(self.dc_plus_schema.genre)


def to_unique_lang_strings(
    langstrings: dcs.UniqueLang,
) -> sippy.UniqueLangStrings:
    return sippy.UniqueLangStrings(
        root=[
            sippy.LangString(lang=lang.lang, value=lang.value) for lang in langstrings
        ]
    )


def to_lang_strings(langstrings: dcs.LangStrings) -> sippy.LangStrings:
    return sippy.LangStrings(
        root=[
            sippy.LangString(lang=lang.lang, value=lang.value) for lang in langstrings
        ]
    )


def to_sippy_edtf(edtf: dcs.EDTF) -> sippy.EDTF:
    match edtf.xsi_type:
        case "{http://id.loc.gov/datatypes/edtf/}EDTF-level0":
            return sippy.EDTF_level0(value=edtf.text)
        case "{http://id.loc.gov/datatypes/edtf/}EDTF-level1":
            return sippy.EDTF_level1(value=edtf.text)
        case "{http://id.loc.gov/datatypes/edtf/}EDTF-level2":
            return sippy.EDTF_level2(value=edtf.text)
