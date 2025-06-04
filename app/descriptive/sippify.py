from typing import Literal

import sippy

from app.descriptive.xml_lang import LangStr as XMLLangStr
import app.descriptive.schema as schema


class Sippify:
    @staticmethod
    def lang_str(str: XMLLangStr | None) -> sippy.LangStr | None:
        if str is None:
            return None
        return sippy.LangStr.codes(**str.content)

    @staticmethod
    def _role(
        role: schema._Role, type: Literal["contributor", "creator", "publisher"]
    ) -> sippy.Role:

        if role.birth_date or role.death_date:
            member = sippy.Person(
                name=sippy.LangStr(nl=role.name),
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
            member = sippy.Thing(name=sippy.LangStr(nl=role.name))

        if role.role_name is None:
            match type:
                case "contributor":
                    role_name = "Bijdrager"
                case "publisher":
                    role_name = "Publisher"
                case "creator":
                    role_name = "Maker"
        else:
            role_name = role.role_name

        return sippy.Role(
            role_name=role_name,
            creator=member if type == "creator" else None,
            publisher=member if type == "publisher" else None,
            contributor=member if type == "contributor" else None,
        )

    @staticmethod
    def creator(creator: schema.Creator) -> sippy.Role:
        return Sippify._role(creator, "creator")

    @staticmethod
    def publisher(publisher: schema.Publisher) -> sippy.Role:
        return Sippify._role(publisher, "publisher")

    @staticmethod
    def contributor(contributor: schema.Contributor) -> sippy.Role:
        return Sippify._role(contributor, "contributor")

    @staticmethod
    def quantitive_value(
        measurement: schema._Measurement | None,
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
        sip_creative_work: schema.AnyCreativeWork | schema.BroadcastEvent,
    ) -> sippy.AnyCreativeWork | sippy.BroadcastEvent:
        match sip_creative_work:
            case schema.BroadcastEvent():
                # TODO
                return sippy.BroadcastEvent()
            case schema.Episode():
                # TODO hardcoded identifier
                return sippy.Episode(
                    name=sippy.LangStr(nl=sip_creative_work.name), identifier=""
                )
            case schema.ArchiveComponent():
                return sippy.ArchiveComponent(
                    name=sippy.LangStr(nl=sip_creative_work.name)
                )
            case schema.CreativeWorkSeries():
                return sippy.CreativeWorkSeries(
                    name=sippy.LangStr(nl=sip_creative_work.name)
                )
            case schema.CreativeWorkSeason():
                return sippy.CreativeWorkSeason(
                    name=sippy.LangStr(nl=sip_creative_work.name)
                )
