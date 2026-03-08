"""Types for dynamic dispatch testing."""


class Foo:
    def save(self):
        raise ValueError("Foo save error")


class Bar:
    def save(self):
        raise TypeError("Bar save error")


class Baz:
    def save(self):
        raise KeyError("Baz save error")


class Qux:
    def save(self):
        raise RuntimeError("Qux save error")
