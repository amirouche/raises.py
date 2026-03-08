# M3 Test 11: test_m3_dispatch_wide_union_with_higher_width

## Given

Same fixture as Test 10 — `dispatch_wide` with `Union[Foo, Bar, Baz, Qux]`.

## Executed

```python
result = raises.analyse('foo.test_module:dispatch_wide', max_union_width=4)
```

## Expected

- `builtins.ValueError` in results (from Foo.save)
- `builtins.TypeError` in results (from Bar.save)
- `builtins.KeyError` in results (from Baz.save)
- `builtins.RuntimeError` in results (from Qux.save)

## Why

With `max_union_width=4`, the 4-member union is within the threshold.
`_is_followable_union` returns followable=True. Each concrete type's `.save()`
method is analysed independently, and their exceptions are unioned into the
results. No warning is emitted.
