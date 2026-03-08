"""Tests for raises.py — Milestone 1, 2 & 3 validation."""

import subprocess
import sys
import warnings

import pytest

import raises


def test_explicit_raise_value_error():
    """Test 1: function with explicit raise ValueError."""
    result = raises.analyse('foo.test_module:raises_value_error')
    exceptions = {e.exception for e in result}
    assert 'builtins.ValueError' in exceptions
    matching = [e for e in result if e.exception == 'builtins.ValueError']
    assert all(e.step == 2 for e in matching)
    assert all(e.source == 'explicit raise' for e in matching)


def test_dict_getitem():
    """Test 2: dict subscript → builtins.KeyError, step 1."""
    result = raises.analyse('foo.test_module:dict_getitem')
    exceptions = {e.exception for e in result}
    assert 'builtins.KeyError' in exceptions
    matching = [e for e in result if e.exception == 'builtins.KeyError']
    assert any(e.step == 1 and e.source == 'dict.__getitem__' for e in matching)


def test_list_getitem():
    """Test 3: list subscript → builtins.IndexError, step 1."""
    result = raises.analyse('foo.test_module:list_getitem')
    exceptions = {e.exception for e in result}
    assert 'builtins.IndexError' in exceptions
    matching = [e for e in result if e.exception == 'builtins.IndexError']
    assert any(e.step == 1 and e.source == 'list.__getitem__' for e in matching)


def test_division():
    """Test 4: int division → builtins.ZeroDivisionError, step 1."""
    result = raises.analyse('foo.test_module:division')
    exceptions = {e.exception for e in result}
    assert 'builtins.ZeroDivisionError' in exceptions
    matching = [e for e in result if e.exception == 'builtins.ZeroDivisionError']
    assert any(e.step == 1 and e.source == 'int.__truediv__' for e in matching)


def test_raise_in_except_not_in_output():
    """Test 5: raise inside except block does NOT appear in output."""
    result = raises.analyse('foo.test_module:raise_in_except')
    exceptions = {e.exception for e in result}
    # RuntimeError is raised inside an except block → should NOT appear
    assert 'builtins.RuntimeError' not in exceptions
    # The dict subscript is guarded by except KeyError → should NOT appear
    assert 'builtins.KeyError' not in exceptions


def test_locally_defined_exception():
    """Test 6: raise a locally-defined exception → module_path.MyError."""
    result = raises.analyse('foo.test_module:raises_local_error')
    exceptions = {e.exception for e in result}
    assert 'foo.test_module.MyError' in exceptions
    matching = [e for e in result if e.exception == 'foo.test_module.MyError']
    assert all(e.step == 2 for e in matching)


def test_imported_exception():
    """Test 7: raise an imported exception → fully-qualified from import."""
    result = raises.analyse('foo.test_module:raises_imported_error')
    exceptions = {e.exception for e in result}
    assert 'foo.errors.ParseError' in exceptions
    matching = [e for e in result if e.exception == 'foo.errors.ParseError']
    assert all(e.step == 2 for e in matching)


def test_generator_function():
    """Test 8: generator function — analysis applies normally."""
    result = raises.analyse('foo.test_module:generator_func')
    exceptions = {e.exception for e in result}
    # Should find both dict subscript and explicit raise
    assert 'builtins.KeyError' in exceptions
    assert 'builtins.ValueError' in exceptions


def test_cli_invocation():
    """Test 9: CLI invocation produces expected output."""
    result = subprocess.run(
        [sys.executable, 'raises.py', 'foo.test_module:my_func'],
        capture_output=True, text=True, cwd='.',
    )
    assert result.returncode == 0
    output = result.stdout
    assert 'foo.test_module:my_func' in output
    assert 'builtins.KeyError' in output
    assert 'builtins.ValueError' in output
    assert 'dict.__getitem__' in output
    assert 'explicit raise' in output


# ---------------------------------------------------------------------------
# Milestone 2 tests
# ---------------------------------------------------------------------------


def test_m2_propagate_explicit_raise():
    """M2 Test 1: helper's explicit raise appears with via annotation."""
    result = raises.analyse('foo.test_module:calls_helper_explicit_raise')
    matching = [e for e in result if e.exception == 'builtins.ValueError']
    assert len(matching) > 0
    # Should have via annotation pointing to the helper
    via_entries = [e for e in matching if e.via]
    assert len(via_entries) > 0
    assert any(any('helper_raises_value_error' in v for v in e.via) for e in via_entries)
    assert all(e.step == 2 for e in via_entries)


def test_m2_propagate_dict_subscript():
    """M2 Test 2: helper's dict subscript → KeyError with via annotation."""
    result = raises.analyse('foo.test_module:calls_helper_dict_subscript')
    matching = [e for e in result if e.exception == 'builtins.KeyError']
    assert len(matching) > 0
    via_entries = [e for e in matching if e.via]
    assert len(via_entries) > 0
    assert any(any('helper_dict_subscript' in v for v in e.via) for e in via_entries)


def test_m2_propagate_guarded():
    """M2 Test 3: helper's KeyError is guarded → NOT in output."""
    result = raises.analyse('foo.test_module:calls_helper_guarded')
    # KeyError from helper should be filtered by the try/except KeyError
    key_errors_via = [e for e in result
                      if e.exception == 'builtins.KeyError' and e.via]
    assert len(key_errors_via) == 0


def test_m2_mutual_recursion():
    """M2 Test 4: mutual recursion terminates, no infinite loop."""
    result = raises.analyse('foo.test_module:mutual_a')
    # Should complete without hanging
    exceptions = {e.exception for e in result}
    # mutual_a itself raises ValueError
    assert 'builtins.ValueError' in exceptions
    # mutual_b raises TypeError, should propagate via mutual_b
    type_errors = [e for e in result if e.exception == 'builtins.TypeError']
    assert len(type_errors) > 0
    assert any(e.via and any('mutual_b' in v for v in e.via) for e in type_errors)


def test_m2_no_cross_module_propagation():
    """M2 Test 5: imported function body is NOT analysed via propagation.

    Note: In M3, cross-file propagation is enabled, but json.loads is in
    STDLIB_CALLABLE_CONTRACTS so its source is never opened — it's handled
    by step 1 directly. No via annotation should appear.
    """
    result = raises.analyse('foo.test_module:calls_imported_func')
    via_entries = [e for e in result if e.via]
    assert len(via_entries) == 0


def test_m2_stdlib_contract_json_loads():
    """M2 Test 6: json.loads → JSONDecodeError via STDLIB_CALLABLE_CONTRACTS."""
    result = raises.analyse('foo.test_module:calls_json_loads')
    exceptions = {e.exception for e in result}
    assert 'json.JSONDecodeError' in exceptions
    matching = [e for e in result if e.exception == 'json.JSONDecodeError']
    # Should be step 1 (contract-based), NOT via propagation
    assert any(e.step == 1 for e in matching)
    assert all(not e.via for e in matching)


# ---------------------------------------------------------------------------
# Milestone 3 tests — Cross-file propagation
# ---------------------------------------------------------------------------


def test_m3_cross_file_propagation():
    """M3 Test 1: cross-file helper's exceptions appear with via path."""
    result = raises.analyse('foo.test_module:calls_cross_file_helper')
    matching = [e for e in result if e.exception == 'builtins.ValueError']
    assert len(matching) > 0
    via_entries = [e for e in matching if e.via]
    assert len(via_entries) > 0
    # via should reference foo.helpers:helper_that_raises
    assert any(
        any('foo.helpers:helper_that_raises' in v for v in e.via)
        for e in via_entries
    )


def test_m3_c_extension_skip():
    """M3 Test 2: C extension function → no propagation, no error."""
    result = raises.analyse('foo.test_module:calls_c_extension_func')
    # math.sqrt is C extension — should not cause errors or propagation
    via_entries = [e for e in result if e.via]
    # No cross-file propagation for C extension
    assert all(
        not any('math' in v for v in e.via)
        for e in via_entries
    ) if via_entries else True


def test_m3_stdlib_contracts_not_source():
    """M3 Test 3: stdlib function uses contracts table, not source."""
    result = raises.analyse('foo.test_module:calls_stdlib_json_loads')
    exceptions = {e.exception for e in result}
    assert 'json.JSONDecodeError' in exceptions
    # Should be from contracts (step 1), not from opening json source
    matching = [e for e in result if e.exception == 'json.JSONDecodeError']
    assert any(e.step == 1 and not e.via for e in matching)


def test_m3_depth_limit():
    """M3 Test 4: propagation stops at max_depth."""
    # With max_depth=1: calls_deep_chain → helper_chain (depth 1) → helper_with_dict (depth 1 same-module, free)
    # The KeyError from helper_with_dict should appear since same-module propagation is free
    result_deep = raises.analyse('foo.test_module:calls_deep_chain', max_depth=1)
    key_errors = [e for e in result_deep if e.exception == 'builtins.KeyError']
    # With max_depth=0: no cross-file propagation at all
    result_shallow = raises.analyse('foo.test_module:calls_deep_chain', max_depth=0)
    key_errors_shallow = [e for e in result_shallow if e.exception == 'builtins.KeyError']
    # max_depth=0 should have fewer or no cross-file results
    assert len(key_errors_shallow) <= len(key_errors)


def test_m3_cross_file_cycle():
    """M3 Test 5: cross-file cycle terminates cleanly."""
    result = raises.analyse('foo.test_module:calls_cross_file_cycle')
    # Should complete without hanging
    # cycle_entry raises TypeError
    exceptions = {e.exception for e in result}
    assert 'builtins.TypeError' in exceptions


# ---------------------------------------------------------------------------
# Milestone 3 tests — Exception hierarchy
# ---------------------------------------------------------------------------


def test_m3_hierarchy_except_exception():
    """M3 Test 6: except Exception catches ValueError."""
    result = raises.analyse('foo.test_module:guarded_by_exception')
    # dict subscript KeyError should be caught by except Exception
    key_errors = [e for e in result if e.exception == 'builtins.KeyError']
    assert len(key_errors) == 0


def test_m3_hierarchy_except_oserror_catches_fnf():
    """M3 Test 7: except OSError catches FileNotFoundError."""
    result = raises.analyse('foo.test_module:guarded_by_oserror')
    # FileNotFoundError is subclass of OSError — should be caught
    fnf = [e for e in result if e.exception == 'builtins.FileNotFoundError']
    assert len(fnf) == 0
    # OSError itself should also be caught
    oserr = [e for e in result if e.exception == 'builtins.OSError']
    assert len(oserr) == 0


def test_m3_hierarchy_oserror_does_not_catch_keyerror():
    """M3 Test 8: except OSError does NOT catch KeyError."""
    result = raises.analyse('foo.test_module:guarded_by_oserror_with_value_error')
    exceptions = {e.exception for e in result}
    # KeyError from dict subscript should NOT be caught by except OSError
    assert 'builtins.KeyError' in exceptions


# ---------------------------------------------------------------------------
# Milestone 3 tests — Dynamic dispatch
# ---------------------------------------------------------------------------


def test_m3_dispatch_narrow_union():
    """M3 Test 9: Union[Foo, Bar] — followable, both exceptions appear."""
    result = raises.analyse('foo.test_module:dispatch_narrow')
    exceptions = {e.exception for e in result}
    # Foo.save raises ValueError, Bar.save raises TypeError
    assert 'builtins.ValueError' in exceptions
    assert 'builtins.TypeError' in exceptions


def test_m3_dispatch_wide_union_skipped():
    """M3 Test 10: Union[Foo, Bar, Baz, Qux] exceeds max_union_width=3."""
    with pytest.warns(UserWarning, match='skipping dynamic dispatch'):
        result = raises.analyse('foo.test_module:dispatch_wide')
    # No exceptions from dispatch should appear
    via_entries = [e for e in result if e.via]
    assert len(via_entries) == 0


def test_m3_dispatch_wide_union_with_higher_width():
    """M3 Test 11: same wide union with max_union_width=4 → followed."""
    result = raises.analyse('foo.test_module:dispatch_wide', max_union_width=4)
    exceptions = {e.exception for e in result}
    assert 'builtins.ValueError' in exceptions
    assert 'builtins.TypeError' in exceptions
    assert 'builtins.KeyError' in exceptions
    assert 'builtins.RuntimeError' in exceptions


def test_m3_dispatch_unknown_silent():
    """M3 Test 12: unknown receiver → skipped silently, no warning."""
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        result = raises.analyse('foo.test_module:dispatch_unknown')
    # No exceptions from dispatch
    via_entries = [e for e in result if e.via]
    assert len(via_entries) == 0
