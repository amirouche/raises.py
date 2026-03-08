# M3 Test 8: test_m3_hierarchy_oserror_does_not_catch_keyerror

## Given

```python
# foo/test_module.py
def guarded_by_oserror_with_value_error(data: dict, key: str):
    try:
        val = data[key]
        return open(val).read()
    except OSError:
        return ""
```

Both a dict subscript and an `open()` call inside `try/except OSError`.

## Executed

```python
result = raises.analyse('foo.test_module:guarded_by_oserror_with_value_error')
```

## Expected

- `builtins.KeyError` IS in the result set (NOT caught by except OSError)

## Why

The dict subscript produces `builtins.KeyError`. The handler is `OSError`.
Exact match fails. Pyright batch check:
```python
_e0 = KeyError()
_h0: OSError = _e0
```
Pyright reports an error: `Type "KeyError" is not assignable to declared type "OSError"`.
KeyError is NOT a subclass of OSError. So the entry is NOT filtered — it stays in results.

Meanwhile, all the `open()` exceptions (FileNotFoundError, PermissionError, etc.) ARE
caught by `except OSError` and filtered out.

**Pyright assumption used:** #5, #8 (error diagnostic format).
