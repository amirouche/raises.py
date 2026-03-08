# Test 5: test_raise_in_except_not_in_output

## Given

```python
# foo/test_module.py
def raise_in_except(data: dict, key: str):
    try:
        return data[key]
    except KeyError:
        raise RuntimeError("wrapped")
```

A function where a dict subscript is inside try/except KeyError, and a
RuntimeError is raised inside the except handler.

## Executed

```python
result = raises.analyse('foo.test_module:raise_in_except')
```

## Expected

- `builtins.RuntimeError` is NOT in the result set
- `builtins.KeyError` is NOT in the result set

## Why

Two suppression mechanisms at work:

1. **KeyError suppressed by guard:** The `data[key]` subscript is inside a
   `try/except KeyError` block. The guard set `{'KeyError'}` is collected by
   `_collect_type_probes`. When step 1 produces `builtins.KeyError`, the short
   name `KeyError` matches the guard, so it's filtered out.

2. **RuntimeError suppressed by except-block rule:** The `raise RuntimeError`
   is inside an except handler body. Step 2 (`_step2_raise_harvesting`) tracks
   `in_except` state — when visiting handler bodies, `in_except=True`. Raise
   statements with `in_except=True` are skipped entirely.
