# Test 4: test_division

## Given

```python
# foo/test_module.py
def division(x: int, y: int):
    return x / y
```

A function that divides two int parameters.

## Executed

```python
result = raises.analyse('foo.test_module:division')
```

## Expected

- `builtins.ZeroDivisionError` is in the result set
- At least one entry has `step=1` and `source='int.__truediv__'`

## Why

Step 1 detects the `x / y` BinOp with `ast.Div` operator. It inserts `reveal_type(x)`
(the left operand), pyright resolves it to `int`. The op maps to `__truediv__` via
`_BINOP_DUNDERS`. The callable key `int.__truediv__` is in STDLIB_CALLABLE_CONTRACTS,
mapping to `['builtins.ZeroDivisionError']`.

**Pyright assumption used:** #1, #2.
