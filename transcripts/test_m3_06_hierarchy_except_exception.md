# M3 Test 6: test_m3_hierarchy_except_exception

## Given

```python
# foo/test_module.py
def guarded_by_exception(data: dict, key: str):
    try:
        return data[key]
    except Exception:
        return None
```

A dict subscript inside `try/except Exception`.

## Executed

```python
result = raises.analyse('foo.test_module:guarded_by_exception')
```

## Expected

- `builtins.KeyError` is NOT in the result set

## Why

Step 1 detects `data[key]` as a dict subscript → `builtins.KeyError`. The probe's
guard set is `{'Exception'}`. Exact name match (`KeyError` != `Exception`) fails,
so `_filter_guarded_entries` falls through to the pyright batch check.

`_check_catches_batch` generates:
```python
_e0 = KeyError()
_h0: Exception = _e0  # __CHECK_0__
```

Pyright reports NO error on the assignment (KeyError is a subclass of Exception),
so the pair is in the catches set. The entry is filtered out.

**Pyright assumption used:** #5 (type assignability for exception hierarchy).
