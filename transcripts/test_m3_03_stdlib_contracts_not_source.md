# M3 Test 3: test_m3_stdlib_contracts_not_source

## Given

```python
# foo/test_module.py
def calls_stdlib_json_loads(text: str):
    import json
    return json.loads(text)
```

Target calls `json.loads`, which is both in STDLIB_CALLABLE_CONTRACTS and has
Python source available on disk.

## Executed

```python
result = raises.analyse('foo.test_module:calls_stdlib_json_loads')
```

## Expected

- `json.JSONDecodeError` is in the result set
- Matching entries have `step=1` and empty `via`
- The json module's source file is NOT opened for analysis

## Why

The contracts table is authoritative for stdlib. Step 1's `_collect_type_probes`
detects `json.loads(text)` as a call matching STDLIB_CALLABLE_CONTRACTS, and
emits the contract's exceptions directly. The propagation engine checks
`_is_stdlib_callable(imported_fqn)` for cross-file callees — since `json.loads`
matches, it skips source analysis entirely. This ensures consistent results
regardless of the stdlib source layout on disk.
