# Test 3: test_list_getitem

## Given

```python
# foo/test_module.py
def list_getitem(items: list, i: int):
    return items[i]
```

A function that subscripts a list parameter.

## Executed

```python
result = raises.analyse('foo.test_module:list_getitem')
```

## Expected

- `builtins.IndexError` is in the result set
- At least one entry has `step=1` and `source='list.__getitem__'`

## Why

Same mechanism as test 2. Pyright resolves `items` to `list[...]`, `_extract_base_type`
returns `list`, combined with op `__getitem__` gives `list.__getitem__`. The contracts
table maps this to `['builtins.IndexError']`.

**Pyright assumption used:** #1, #2.
