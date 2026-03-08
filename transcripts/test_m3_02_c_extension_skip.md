# M3 Test 2: test_m3_c_extension_skip

## Given

```python
# foo/test_module.py
def calls_c_extension_func():
    import math
    return math.sqrt(4.0)
```

Target calls `math.sqrt`, which is implemented as a C extension.

## Executed

```python
result = raises.analyse('foo.test_module:calls_c_extension_func')
```

## Expected

- No propagation entries referencing `math` in via
- No errors or crashes

## Why

`math.sqrt` is not in STDLIB_CALLABLE_CONTRACTS. When the propagation engine
tries cross-file resolution, `_find_module_source('math')` finds the spec but
sees `spec.origin` ends with `.so` (C extension), so it returns None. The
callee is silently skipped — no entries emitted, no errors raised.
