# Test 8: test_generator_function

## Given

```python
# foo/test_module.py
def generator_func(data: dict):
    yield data["first"]
    raise ValueError("done")
```

A generator function with both a dict subscript and an explicit raise.

## Executed

```python
result = raises.analyse('foo.test_module:generator_func')
```

## Expected

- `builtins.KeyError` is in the result set (from dict subscript)
- `builtins.ValueError` is in the result set (from explicit raise)

## Why

Generator functions are analysed identically to regular functions. The AST
still contains the subscript and raise nodes. Step 1 finds `data["first"]`
as a dict subscript (via reveal_type on `data`), step 2 finds the explicit
`raise ValueError`. The `yield` keyword does not affect analysis.
