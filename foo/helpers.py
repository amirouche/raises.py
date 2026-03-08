"""Helper module for cross-file propagation tests."""


def helper_that_raises():
    """Raises ValueError explicitly."""
    raise ValueError("from helpers module")


def helper_with_dict(data: dict, key: str):
    """Does a dict subscript — raises KeyError."""
    return data[key]


def helper_chain(data: dict, key: str):
    """Calls helper_with_dict — for depth testing."""
    return helper_with_dict(data, key)
