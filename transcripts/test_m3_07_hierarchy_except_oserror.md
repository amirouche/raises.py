# M3 Test 7: test_m3_hierarchy_except_oserror_catches_fnf

## Given

```python
# foo/test_module.py
def guarded_by_oserror():
    try:
        return open("/nonexistent").read()
    except OSError:
        return ""
```

`open()` call inside `try/except OSError`.

## Executed

```python
result = raises.analyse('foo.test_module:guarded_by_oserror')
```

## Expected

- `builtins.FileNotFoundError` is NOT in the result set
- `builtins.OSError` is NOT in the result set

## Why

`open()` maps to STDLIB_CALLABLE_CONTRACTS key `builtins.open`, which lists
`FileNotFoundError`, `PermissionError`, `IsADirectoryError`, and `OSError`.

For `OSError` vs handler `OSError`: exact name match succeeds → filtered.

For `FileNotFoundError` vs handler `OSError`: exact match fails. Pyright batch check:
```python
_e0 = FileNotFoundError()
_h0: OSError = _e0
```
No pyright error (FileNotFoundError is a subclass of OSError) → caught → filtered.

Same for `PermissionError` and `IsADirectoryError` (both subclasses of OSError).

**Pyright assumption used:** #5 (type assignability for exception hierarchy).
