# M3 Test 12: test_m3_dispatch_unknown_silent

## Given

```python
# foo/test_module.py
def dispatch_unknown(obj):
    obj.save()
```

Target calls `obj.save()` where `obj` has no type annotation (pyright infers Unknown).

## Executed

```python
with warnings.catch_warnings():
    warnings.simplefilter("error")  # Turn warnings into errors
    result = raises.analyse('foo.test_module:dispatch_unknown')
```

## Expected

- No warnings emitted (no UserWarning, no other warnings)
- No entries with non-empty `via`

## Why

Pyright resolves `obj` to a type containing `Unknown` (or simply cannot
determine a concrete type). `_is_followable_union` detects `Unknown` or `Any`
in the type members and returns reason='unknown'. The propagation engine
skips the call site **silently** — no warning, no entries. This is the
correct behavior: when types are not fully resolved, there is nothing useful
to report and no actionable warning to give.

**Pyright assumption used:** #4 (Unknown/Any representation).
