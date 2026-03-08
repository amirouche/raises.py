"""Test module for raises.py validation."""

from __future__ import annotations

from typing import Union

from foo.errors import ParseError
from foo.cycle_target import cycle_entry
from foo.dispatch_types import Foo, Bar, Baz, Qux


class MyError(Exception):
    pass


def raises_value_error():
    """Test 1: explicit raise ValueError."""
    raise ValueError("bad value")


def dict_getitem(data: dict, key: str):
    """Test 2: dict subscript → KeyError."""
    return data[key]


def list_getitem(items: list, i: int):
    """Test 3: list subscript → IndexError."""
    return items[i]


def division(x: int, y: int):
    """Test 4: int division → ZeroDivisionError."""
    return x / y


def raise_in_except(data: dict, key: str):
    """Test 5: raise inside except block → should NOT appear."""
    try:
        return data[key]
    except KeyError:
        raise RuntimeError("wrapped")


def raises_local_error():
    """Test 6: raise a locally-defined exception."""
    raise MyError("local error")


def raises_imported_error():
    """Test 7: raise an imported exception."""
    raise ParseError("parse failed")


def generator_func(data: dict):
    """Test 8: generator function — analysis applies normally."""
    yield data["first"]
    raise ValueError("done")


def my_func(data: dict, key: str):
    """Test 9: CLI test target."""
    val = data[key]
    raise ValueError("something")


# --- Milestone 2 test fixtures ---

def helper_raises_value_error():
    """Helper that explicitly raises ValueError."""
    raise ValueError("from helper")


def calls_helper_explicit_raise():
    """M2 Test 1: calls a same-module helper that raises."""
    helper_raises_value_error()


def helper_dict_subscript(data: dict, key: str):
    """Helper that does a dict subscript."""
    return data[key]


def calls_helper_dict_subscript(data: dict, key: str):
    """M2 Test 2: calls a same-module helper that has dict subscript."""
    return helper_dict_subscript(data, key)


def calls_helper_guarded(data: dict, key: str):
    """M2 Test 3: calls helper inside try/except KeyError."""
    try:
        return helper_dict_subscript(data, key)
    except KeyError:
        return None


def mutual_a():
    """M2 Test 4: mutual recursion — calls mutual_b."""
    mutual_b()
    raise ValueError("from a")


def mutual_b():
    """M2 Test 4: mutual recursion — calls mutual_a."""
    mutual_a()
    raise TypeError("from b")


def calls_imported_func():
    """M2 Test 5: calls a function from another module (not same-module)."""
    import json
    return json.loads('{}')


def calls_json_loads(text: str):
    """M2 Test 6: calls json.loads — should use STDLIB_CALLABLE_CONTRACTS."""
    import json
    return json.loads(text)


# --- Milestone 3 test fixtures ---

# Cross-file propagation
from foo.helpers import helper_that_raises, helper_chain


def calls_cross_file_helper():
    """M3 Test 1: calls a function in another module with source."""
    helper_that_raises()


def calls_c_extension_func():
    """M3 Test 2: calls a C extension function (math.sqrt)."""
    import math
    return math.sqrt(4.0)


def calls_stdlib_json_loads(text: str):
    """M3 Test 3: calls stdlib function in contracts table."""
    import json
    return json.loads(text)


def calls_deep_chain(data: dict, key: str):
    """M3 Test 4: calls helper_chain which calls helper_with_dict."""
    helper_chain(data, key)


def calls_cycle_target_back():
    """Part of cross-file cycle: called by foo.cycle_target.cycle_entry."""
    raise ValueError("from test_module cycle")


def calls_cross_file_cycle():
    """M3 Test 5: cross-file cycle test.
    cycle_entry calls calls_cycle_target_back (same module) which raises ValueError.
    This creates a potential cycle: test_module → cycle_target → test_module.
    """
    cycle_entry()


# Exception hierarchy tests

def guarded_by_exception(data: dict, key: str):
    """M3 Test 6: call inside except Exception."""
    try:
        return data[key]
    except Exception:
        return None


def guarded_by_oserror():
    """M3 Test 7/8: call inside except OSError — catches FileNotFoundError."""
    try:
        return open("/nonexistent").read()
    except OSError:
        return ""


def guarded_by_oserror_with_value_error(data: dict, key: str):
    """M3 Test 8: except OSError does NOT catch ValueError."""
    try:
        val = data[key]
        return open(val).read()
    except OSError:
        return ""


# Dynamic dispatch tests

def dispatch_narrow(obj: Union[Foo, Bar]):
    """M3 Test 9: narrow union — followable."""
    obj.save()


def dispatch_wide(obj: Union[Foo, Bar, Baz, Qux]):
    """M3 Test 10/11: wide union — exceeds default max_union_width."""
    obj.save()


def dispatch_unknown(obj):
    """M3 Test 12: unknown receiver type."""
    obj.save()
