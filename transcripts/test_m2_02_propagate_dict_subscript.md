# M2 Test 2: test_m2_propagate_dict_subscript

## Given

```python
# foo/test_module.py
def helper_dict_subscript(data: dict, key: str):
    return data[key]

def calls_helper_dict_subscript(data: dict, key: str):
    return helper_dict_subscript(data, key)
```

Target calls a same-module helper that has a dict subscript.

## Executed

```python
result = raises.analyse('foo.test_module:calls_helper_dict_subscript')
```

## Expected

- `builtins.KeyError` is in the result set
- At least one entry has non-empty `via` containing `helper_dict_subscript`

## Why

Propagation analyses `helper_dict_subscript`, which has a dict subscript
(step 1 → KeyError via `dict.__getitem__`). This entry is propagated to the
caller with a `via` annotation pointing to the helper.
