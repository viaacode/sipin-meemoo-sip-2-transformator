import transformator.v2_1.preservation.film as film
from eark_models.utils import parse_xml_tree


def test_film_extension():
    root = parse_xml_tree("tests/v2_1/film/film_extension.xml")
    film.CarrierSignificantProperties.from_xml_tree(root)
