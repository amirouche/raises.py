# M2 Test 5: test_m2_no_cross_module_propagation

## Given

```python
# foo/test_module.py
def calls_imported_func():
    import json
    return json.loads('{}')
```

Target calls `json.loads` — a stdlib function.

## Executed

```python
result = raises.analyse('foo.test_module:calls_imported_func')
```

## Expected

- No entries with non-empty `via` (no cross-module propagation via source analysis)

## Why

`json.loads` is in STDLIB_CALLABLE_CONTRACTS. The contracts table is
authoritative for stdlib — source files are never opened. Step 1 detects
`json.loads(...)` via `_call_to_contract_key`, looks it up in the contracts
table, and emits `json.JSONDecodeError` directly (step 1, no via). The
propagation engine also checks `_is_stdlib_callable` and skips callees
that match contracts.
