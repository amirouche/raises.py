# Test 1: test_explicit_raise_value_error

## Given

```python
# foo/test_module.py
def raises_value_error():
    raise ValueError("bad value")
```

A function with a single explicit `raise ValueError`.

## Executed

```python
result = raises.analyse('foo.test_module:raises_value_error')
```

## Expected

- `builtins.ValueError` is in the result set
- All matching entries have `step=2` (explicit raise harvesting)
- All matching entries have `source='explicit raise'`
- `via` is empty tuple (direct finding, no propagation)

## Why

Step 2 (raise harvesting) walks the AST of the function body, finds `raise ValueError(...)`,
resolves `ValueError` to `builtins.ValueError` via the BUILTIN_EXCEPTIONS set, and emits a
RaisesEntry with source='explicit raise' and step=2. The raise is not inside an except block,
so it is not filtered.
