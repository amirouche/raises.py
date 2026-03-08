# Test 7: test_imported_exception

## Given

```python
# foo/test_module.py
from foo.errors import ParseError

def raises_imported_error():
    raise ParseError("parse failed")

# foo/errors.py
class ParseError(Exception):
    pass
```

A function that raises an exception imported from another module.

## Executed

```python
result = raises.analyse('foo.test_module:raises_imported_error')
```

## Expected

- `foo.errors.ParseError` is in the result set
- All matching entries have `step=2`

## Why

Step 2 finds `raise ParseError(...)`. The name `ParseError` is resolved via
`_build_import_map` which maps it to `foo.errors.ParseError` (from the
`from foo.errors import ParseError` statement). This fully-qualified name
becomes the exception in the RaisesEntry.
