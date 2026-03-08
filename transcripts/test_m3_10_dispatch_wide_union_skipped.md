# M3 Test 10: test_m3_dispatch_wide_union_skipped

## Given

```python
# foo/test_module.py
from foo.dispatch_types import Foo, Bar, Baz, Qux

def dispatch_wide(obj: Union[Foo, Bar, Baz, Qux]):
    obj.save()
```

Target calls `obj.save()` where obj is `Union[Foo, Bar, Baz, Qux]` (4 concrete
types, exceeds default `max_union_width=3`).

## Executed

```python
with pytest.warns(UserWarning, match='skipping dynamic dispatch'):
    result = raises.analyse('foo.test_module:dispatch_wide')
```

## Expected

- A UserWarning is emitted containing "skipping dynamic dispatch"
- No entries with non-empty `via` (dispatch not followed)

## Why

Pyright resolves `obj` to `Foo | Bar | Baz | Qux`. `_is_followable_union` finds
4 members, all concrete (no Unknown/Any), but 4 > max_union_width (3). It returns
reason='too_wide'. The propagation engine emits a `warnings.warn()` with the
appropriate message and skips the call site entirely.

**Pyright assumption used:** #3 (union type syntax).
