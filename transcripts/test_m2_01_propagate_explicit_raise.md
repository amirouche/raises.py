# M2 Test 1: test_m2_propagate_explicit_raise

## Given

```python
# foo/test_module.py
def helper_raises_value_error():
    raise ValueError("from helper")

def calls_helper_explicit_raise():
    helper_raises_value_error()
```

Target function calls a same-module helper that explicitly raises.

## Executed

```python
result = raises.analyse('foo.test_module:calls_helper_explicit_raise')
```

## Expected

- `builtins.ValueError` is in the result set
- At least one matching entry has a non-empty `via` tuple
- The `via` tuple contains a string with `helper_raises_value_error`
- All via entries have `step=2` (the helper's raise is an explicit raise)

## Why

The propagation engine (`_propagate`) collects call sites in the target body.
It finds `helper_raises_value_error()`, confirms it's defined in the same module
via `_find_same_module_functions`. It runs steps 1 and 2 on the helper's body,
finding the explicit raise. The resulting entries are annotated with
`via=('foo.test_module:helper_raises_value_error',)` and merged into the target's results.
