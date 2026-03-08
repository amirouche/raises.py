# M2 Test 3: test_m2_propagate_guarded

## Given

```python
# foo/test_module.py
def helper_dict_subscript(data: dict, key: str):
    return data[key]

def calls_helper_guarded(data: dict, key: str):
    try:
        return helper_dict_subscript(data, key)
    except KeyError:
        return None
```

Target calls a helper inside a try/except KeyError block.

## Executed

```python
result = raises.analyse('foo.test_module:calls_helper_guarded')
```

## Expected

- No `builtins.KeyError` entries with non-empty `via` (all filtered)

## Why

The helper raises KeyError (from dict subscript), but the call site in the
target is guarded by `except KeyError`. The `_collect_call_sites` function
captures the guard set `{'KeyError'}` for this call. When propagating, each
callee entry is checked against the guards — `KeyError` matches exactly, so
it's filtered out. (In M3, this also works with hierarchy: `except Exception`
would also catch it.)
