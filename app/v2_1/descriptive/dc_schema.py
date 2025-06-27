from pathlib import Path
from functools import partial

import sippy

from .models import dc_schema as dcs
from .models.xml_lang import XMLLang


def parse_dc_schema(path: Path) -> partial[sippy.IntellectualEntity]:
    dc_plus_schema = dcs.DCPlusSchema.from_xml(path)
    sippify = DC2Sippy(dc_plus_schema)

    return partial(
        sippy.IntellectualEntity,
        name=sippify.title,
        alternative_name=sippify.alternative,
        duration=sippify.extent,
        available=sippify.available,
        description=sippify.description,
        abstract=sippify.abstract,
        date_created=sippify.created,
        date_published=sippify.issued,
        publisher=sippify.publisher,
        creator=sippify.creator,
        contributor=sippify.contributor,
        spatial=sippify.spatial,
        temporal=sippify.temporal,
        keywords=sippify.subject,
        in_language=sippify.in_language,
        license=sippify.license,
        copyright_holder=sippify.copyright_holder,
        rights=sippify.rights,
        format=sippify.format,
        height=sippify.height,
        width=sippify.width,
        depth=sippify.depth,
        weight=sippify.weight,
        art_medium=sippify.art_medium,
        artform=sippify.artform,
        schema_is_part_of=sippify.schema_is_part_of,
        credit_text=sippify.credit_text,
    )


class DC2Sippy:

    def __init__(self, dc_plus_schema: dcs.DCPlusSchema) -> None:
        self.dc_plus_schema = dc_plus_schema

    @property
    def title(self) -> sippy.LangStr:
        return DC2Sippy.lang_str(self.dc_plus_schema.title)

    @property
    def alternative(self) -> list[sippy.LangStr]:
        if self.dc_plus_schema.alternative is None:
            return []
        return [DC2Sippy.lang_str(self.dc_plus_schema.alternative)]

    @property
    def available(self) -> sippy.DateTime | None:
        if self.dc_plus_schema.available is None:
            return None
        return sippy.DateTime(value=self.dc_plus_schema.available)

    @property
    def description(self) -> sippy.LangStr | None:
        return DC2Sippy.lang_str(self.dc_plus_schema.description)

    @property
    def abstract(self) -> sippy.LangStr | None:
        return DC2Sippy.optional_lang_str(self.dc_plus_schema.abstract)

    @property
    def created(self) -> sippy.EDTF:
        return sippy.EDTF_level1(value=self.dc_plus_schema.created)

    @property
    def issued(self) -> sippy.EDTF | None:
        if self.dc_plus_schema.issued is None:
            return None
        return sippy.EDTF_level1(value=self.dc_plus_schema.issued)

    @property
    def publisher(self) -> list[sippy.Role]:
        return [DC2Sippy.role(role) for role in self.dc_plus_schema.publisher]

    @property
    def creator(self) -> list[sippy.Role]:
        return [DC2Sippy.role(role) for role in self.dc_plus_schema.creator]

    @property
    def contributor(self) -> list[sippy.Role]:
        return [DC2Sippy.role(role) for role in self.dc_plus_schema.contributor]

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
        return [DC2Sippy.lang_str(self.dc_plus_schema.subject)]

    @property
    def in_language(self) -> list[str]:
        return self.dc_plus_schema.language

    @property
    def license(self) -> list[sippy.Concept]:
        return [
            sippy.Concept(id="https://data.hetarchief.be/id/license/" + l)
            for l in self.dc_plus_schema.license
        ]

    @property
    def copyright_holder(self) -> list[sippy.Thing]:
        if self.dc_plus_schema.rights_holder is None:
            return []
        return [sippy.Thing(name=DC2Sippy.lang_str(self.dc_plus_schema.rights_holder))]

    @property
    def rights(self) -> list[sippy.LangStr]:
        if self.dc_plus_schema.rights is None:
            return []
        return [DC2Sippy.lang_str(self.dc_plus_schema.rights)]

    @property
    def format(self) -> sippy.String:
        return sippy.String(value=self.dc_plus_schema.format)

    @property
    def height(self) -> sippy.QuantitativeValue | None:
        return DC2Sippy.quantitive_value(self.dc_plus_schema.height)

    @property
    def width(self):
        return DC2Sippy.quantitive_value(self.dc_plus_schema.width)

    @property
    def depth(self):
        return DC2Sippy.quantitive_value(self.dc_plus_schema.depth)

    @property
    def weight(self):
        return DC2Sippy.quantitive_value(self.dc_plus_schema.weight)

    @property
    def art_medium(self) -> list[sippy.LangStr]:
        if self.dc_plus_schema.art_medium is None:
            return []
        return [DC2Sippy.lang_str(self.dc_plus_schema.art_medium)]

    @property
    def artform(self) -> list[sippy.LangStr]:
        if self.dc_plus_schema.artform is None:
            return []
        return [DC2Sippy.lang_str(self.dc_plus_schema.artform)]

    @property
    def schema_is_part_of(self) -> list[sippy.AnyCreativeWork | sippy.BroadcastEvent]:
        return [DC2Sippy.creative_work(cw) for cw in self.dc_plus_schema.is_part_of]

    @property
    def credit_text(self) -> list[sippy.LangStr]:
        return [sippy.LangStr(nl=s) for s in self.dc_plus_schema.credit_text]

    @property
    def extent(self) -> sippy.Duration | None:
        if self.dc_plus_schema.extent is None:
            return None
        return sippy.Duration(value=self.dc_plus_schema.extent)

    @staticmethod
    def optional_lang_str(str: XMLLang | None) -> sippy.LangStr | None:
        if str is None:
            return None
        return sippy.LangStr.codes(**str.content)

    @staticmethod
    def lang_str(str: XMLLang) -> sippy.LangStr:
        return sippy.LangStr.codes(**str.content)

    @staticmethod
    def role(role: dcs.Creator | dcs.Publisher | dcs.Contributor) -> sippy.Role:
        is_person = role.birth_date or role.death_date
        if is_person:
            member = sippy.Person(
                name=DC2Sippy.lang_str(role.name),
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
            member = sippy.Thing(name=DC2Sippy.lang_str(role.name))

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
        )

    @staticmethod
    def quantitive_value(
        measurement: dcs._Measurement | None,
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

    @staticmethod
    def creative_work(
        sip_creative_work: dcs.AnyCreativeWork | dcs.BroadcastEvent,
    ) -> sippy.AnyCreativeWork | sippy.BroadcastEvent:
        match sip_creative_work:
            case dcs.BroadcastEvent():
                # TODO
                return sippy.BroadcastEvent()
            case dcs.Episode():
                # TODO hardcoded identifier
                return sippy.Episode(
                    name=DC2Sippy.lang_str(sip_creative_work.name), identifier=""
                )
            case dcs.ArchiveComponent():
                return sippy.ArchiveComponent(
                    name=DC2Sippy.lang_str(sip_creative_work.name)
                )
            case dcs.CreativeWorkSeries():
                return sippy.CreativeWorkSeries(
                    name=DC2Sippy.lang_str(sip_creative_work.name)
                )
            case dcs.CreativeWorkSeason():
                return sippy.CreativeWorkSeason(
                    name=DC2Sippy.lang_str(sip_creative_work.name)
                )
