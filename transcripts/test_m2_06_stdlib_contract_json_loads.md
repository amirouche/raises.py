# M2 Test 6: test_m2_stdlib_contract_json_loads

## Given

```python
# foo/test_module.py
def calls_json_loads(text: str):
    import json
    return json.loads(text)
```

Target calls `json.loads` with a parameter.

## Executed

```python
result = raises.analyse('foo.test_module:calls_json_loads')
```

## Expected

- `json.JSONDecodeError` is in the result set
- At least one matching entry has `step=1`
- All matching entries have empty `via` (not propagated)

## Why

Step 1's `_collect_type_probes` detects the `json.loads(text)` call.
`_call_to_contract_key` builds the dotted path `json.loads` by walking the
AST attribute chain. This key exists in STDLIB_CALLABLE_CONTRACTS, mapping to
`['json.JSONDecodeError']`. The entry is emitted with step=1 and
`source='json.loads'`.
