# Test 6: test_locally_defined_exception

## Given

```python
# foo/test_module.py
class MyError(Exception):
    pass

def raises_local_error():
    raise MyError("local error")
```

A function that raises a class defined in the same module.

## Executed

```python
result = raises.analyse('foo.test_module:raises_local_error')
```

## Expected

- `foo.test_module.MyError` is in the result set
- All matching entries have `step=2`

## Why

Step 2 finds `raise MyError(...)`. The name `MyError` is not in
BUILTIN_EXCEPTIONS and not in the import map. It IS in `_build_local_defs`
(which collects class definitions at module level). So `_resolve_exception_name`
returns `foo.test_module.MyError` (module_path + '.' + name).
