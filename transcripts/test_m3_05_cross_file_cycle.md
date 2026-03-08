# M3 Test 5: test_m3_cross_file_cycle

## Given

```python
# foo/test_module.py
from foo.cycle_target import cycle_entry

def calls_cycle_target_back():
    raise ValueError("from test_module cycle")

def calls_cross_file_cycle():
    cycle_entry()

# foo/cycle_target.py
def cycle_entry():
    from foo.test_module import calls_cycle_target_back
    calls_cycle_target_back()
    raise TypeError("from cycle_target")
```

Target calls `cycle_entry` (cross-file), which calls back into `test_module`
(creating a potential cycle: test_module → cycle_target → test_module).

## Executed

```python
result = raises.analyse('foo.test_module:calls_cross_file_cycle')
```

## Expected

- Terminates without hanging
- `builtins.TypeError` in results (from `cycle_entry`'s explicit raise)

## Why

Cycle detection uses a visited set tracking `module:callable` keys. When
`calls_cross_file_cycle` is analysed, it adds `foo.test_module:calls_cross_file_cycle`
to visited. It then propagates to `cycle_entry` in `foo.cycle_target`, which has an
explicit `raise TypeError`. The `calls_cycle_target_back()` call inside cycle_entry
uses a function-local import, which is not in the module-level import map — so the
propagation doesn't try to follow it back. Even if it did, the visited set would
prevent re-entry.
