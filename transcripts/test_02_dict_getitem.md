# Test 2: test_dict_getitem

## Given

```python
# foo/test_module.py
def dict_getitem(data: dict, key: str):
    return data[key]
```

A function that subscripts a dict parameter.

## Executed

```python
result = raises.analyse('foo.test_module:dict_getitem')
```

## Expected

- `builtins.KeyError` is in the result set
- At least one entry has `step=1` and `source='dict.__getitem__'`

## Why

Step 1 (pyright-assisted inference) detects the `data[key]` subscript, inserts
`reveal_type(data)` into a temp file, runs pyright, and gets back `dict[str, Any]` or
similar. `_extract_base_type` extracts `dict`. The probe's op is `__getitem__`, so the
callable key becomes `dict.__getitem__`. This is looked up in STDLIB_CALLABLE_CONTRACTS
which maps it to `['builtins.KeyError']`.

**Pyright assumption used:** #1 (reveal_type output format), #2 (parameterized type format).
