# Test 9: test_cli_invocation

## Given

```python
# foo/test_module.py
def my_func(data: dict, key: str):
    val = data[key]
    raise ValueError("something")
```

## Executed

```bash
python raises.py foo.test_module:my_func
```

(Via subprocess from the test.)

## Expected

- Exit code 0
- Output contains `foo.test_module:my_func` (target header)
- Output contains `builtins.KeyError` and `builtins.ValueError`
- Output contains `dict.__getitem__` (step 1 source) and `explicit raise` (step 2 source)

## Why

Validates that the CLI entry point (`main()`) works end-to-end. The function
has both a dict subscript (step 1 → KeyError) and an explicit raise (step 2 →
ValueError). The `_format_output` function produces the expected text format.
