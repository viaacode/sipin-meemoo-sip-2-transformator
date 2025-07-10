class NamespaceMeta(type):
    __ns__: str

    def __getattr__(cls, item: str) -> str:
        return "{" + cls.__ns__ + "}" + item


class Namespace(metaclass=NamespaceMeta):
    pass


class xsi(Namespace):
    __ns__ = "http://www.w3.org/2001/XMLSchema-instance"


class schema(Namespace):
    __ns__ = "https://schema.org/"


class dcterms(Namespace):
    __ns__ = "http://purl.org/dc/terms/"
