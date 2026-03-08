# M3 Test 1: test_m3_cross_file_propagation

## Given

```python
# foo/test_module.py
from foo.helpers import helper_that_raises

def calls_cross_file_helper():
    helper_that_raises()

# foo/helpers.py
def helper_that_raises():
    raise ValueError("from helpers module")
```

Target calls a function defined in a different module with Python source available.

## Executed

```python
result = raises.analyse('foo.test_module:calls_cross_file_helper')
```

## Expected

- `builtins.ValueError` is in the result set
- At least one entry has non-empty `via` containing `foo.helpers:helper_that_raises`

## Why

The propagation engine finds `helper_that_raises()` in the target's call sites.
The name is in the module's import map (from `from foo.helpers import helper_that_raises`),
resolving to `foo.helpers.helper_that_raises`. This is not in STDLIB_CALLABLE_CONTRACTS.
`_find_module_source('foo.helpers')` finds the .py file. The engine parses it, finds the
function, runs steps 1+2, and gets the explicit ValueError raise. This is propagated back
with `via=('foo.helpers:helper_that_raises',)`.
