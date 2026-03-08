# M3 Test 4: test_m3_depth_limit

## Given

```python
# foo/test_module.py
from foo.helpers import helper_chain

def calls_deep_chain(data: dict, key: str):
    helper_chain(data, key)

# foo/helpers.py
def helper_chain(data: dict, key: str):
    return helper_with_dict(data, key)

def helper_with_dict(data: dict, key: str):
    return data[key]
```

Target calls `helper_chain` (cross-file, depth 1), which calls
`helper_with_dict` (same-module in helpers.py, free).

## Executed

```python
result_deep = raises.analyse('foo.test_module:calls_deep_chain', max_depth=1)
result_shallow = raises.analyse('foo.test_module:calls_deep_chain', max_depth=0)
```

## Expected

- With `max_depth=1`: KeyError appears (cross-file hop to helpers.py is within limit,
  same-module propagation within helpers.py is free)
- With `max_depth=0`: No cross-file propagation at all, fewer or no KeyError results

## Why

Depth counts cross-file hops only. `calls_deep_chain` → `helper_chain` is one
cross-file hop (depth 1). Within `foo/helpers.py`, `helper_chain` → `helper_with_dict`
is same-module propagation which is free (doesn't consume depth). So at max_depth=1,
the full chain is followed. At max_depth=0, no cross-file hops are allowed, so
`helper_chain` is not analysed.
