# M3 Test 9: test_m3_dispatch_narrow_union

## Given

```python
# foo/test_module.py
from foo.dispatch_types import Foo, Bar

def dispatch_narrow(obj: Union[Foo, Bar]):
    obj.save()

# foo/dispatch_types.py
class Foo:
    def save(self):
        raise ValueError("Foo save error")

class Bar:
    def save(self):
        raise TypeError("Bar save error")
```

Target calls `obj.save()` where obj is `Union[Foo, Bar]` (2 concrete types,
within default `max_union_width=3`).

## Executed

```python
result = raises.analyse('foo.test_module:dispatch_narrow')
```

## Expected

- `builtins.ValueError` in results (from Foo.save)
- `builtins.TypeError` in results (from Bar.save)

## Why

The propagation engine detects `obj.save()` as an attribute call. It uses
`_resolve_receiver_type` to ask pyright for the type of `obj`, getting back
`Foo | Bar`. `_is_followable_union` confirms: 2 members, no Unknown/Any,
within max_union_width=3.

For each member type (Foo, Bar), it looks for `Foo.save` and `Bar.save` —
first in the same module (not found), then via import map. Foo and Bar are
imported from `foo.dispatch_types`. It opens that module's source, finds the
class methods, and analyses them. Foo.save raises ValueError, Bar.save raises
TypeError. Both are propagated with via annotations.

**Pyright assumption used:** #1 (reveal_type), #3 (union type syntax), #4 (Unknown/Any).
