# raises.py — Milestone 1

Create a new single-file project `raises.py`.

## Goal

`raises.py` answers one question: **what exceptions can this function or method
raise?** It is a standalone static analysis tool that will eventually feed
`InjectException` in `mutation.py` with richer exception data than the current
hardcoded contracts table.

Milestone 1 scope: given a target in `foo.bar:baz` or `foo.bar:Baz.qux`
notation, print the fully-qualified module paths of exceptions that target can
raise.

Target notation: `module.path:callable` where callable is either a bare
function name (`baz`) or a class and method separated by a dot (`Baz.qux`).

```
$ python raises.py foo.bar:baz
foo.bar:baz
  builtins.KeyError        [dict.__getitem__, step 1]
  builtins.ValueError      [explicit raise, step 2]
  foo.bar.CustomError      [explicit raise, step 2]

$ python raises.py foo.bar:Baz.qux
foo.bar:Baz.qux
  builtins.IndexError      [list.__getitem__, step 1]
```

-----

## Architecture: two steps in sequence, both required

Pyright is not optional. `raises.py` requires pyright to be installed and
callable. If pyright is absent or fails, exit with a clear error message — do
not silently degrade.

### Step 1 — Pyright-assisted callable inference

Use pyright's programmatic API (not subprocess, not `--outputjson`) to resolve
the callable being invoked at each call site and subscript access within the
target function body.

The contracts are keyed on **callables**, not types. Pyright resolves what
callable is actually being invoked — `dict.__getitem__`, `list.__getitem__`,
`int.__truediv__`, `open` — and from that you look up what exceptions it can
raise. Examples:

```python
CALLABLE_CONTRACTS = {
    'dict.__getitem__':      ['builtins.KeyError'],
    'list.__getitem__':      ['builtins.IndexError'],
    'tuple.__getitem__':     ['builtins.IndexError'],
    'str.__getitem__':       ['builtins.IndexError'],
    'int.__truediv__':       ['builtins.ZeroDivisionError'],
    'int.__floordiv__':      ['builtins.ZeroDivisionError'],
    'int.__mod__':           ['builtins.ZeroDivisionError'],
    'float.__truediv__':     ['builtins.ZeroDivisionError'],
    'float.__floordiv__':    ['builtins.ZeroDivisionError'],
    'builtins.open':         ['builtins.FileNotFoundError',
                              'builtins.PermissionError',
                              'builtins.IsADirectoryError'],
    'builtins.next':         ['builtins.StopIteration'],
    'builtins.int':          ['builtins.ValueError', 'builtins.TypeError'],
    'builtins.float':        ['builtins.ValueError', 'builtins.TypeError'],
    'builtins.iter':         ['builtins.TypeError'],
}
```

The target callable may itself be a generator, a function, a method, or a
coroutine — the analysis applies to whatever the body contains regardless of
the callable kind.

Only apply contracts to unguarded call sites — skip any call inside a
`try/except` block that already handles the relevant exception.

### Step 2 — Explicit raise harvesting

Walk the AST of the target function or method body. Collect every `raise`
statement directly in the body. Skip `raise` statements inside `except` blocks
— those are re-raises of already-caught exceptions and are not propagated to
callers.

Resolve the raised exception name to a fully-qualified module path using two
rules:

**Rule A — Name resolution via imports:** read the module's import statements
to find where the name comes from, then stop. If the module contains
`from foo.errors import ParseError`, then `raise ParseError` resolves to
`foo.errors.ParseError`. Do not open `foo/errors.py` or follow further.

**Rule B — Same-module definitions:** if the name is defined in the same
module (`class MyError(Exception): ...`), resolve it as `<module_path>.MyError`.

If neither rule applies → emit `?UnknownName`.

Builtin exception names (`ValueError`, `KeyError`, etc.) resolve to
`builtins.ValueError`, `builtins.KeyError`, etc.

-----

## CLI interface

```
python raises.py <target> [<target> ...]
```

Output: one fully-qualified exception path per line, grouped by target:

```
foo.bar:baz
  builtins.KeyError        [dict.__getitem__, step 1]
  builtins.ValueError      [explicit raise, step 2]
  foo.errors.ParseError    [explicit raise, step 2]

foo.bar:Baz.qux
  builtins.IndexError      [list.__getitem__, step 1]
```

-----

## Programmatic API

```python
import raises

result = raises.analyse('foo.bar:baz')
# returns list of RaisesEntry namedtuples:
# RaisesEntry(exception='builtins.KeyError', source='dict.__getitem__', step=1)

result = raises.analyse('foo.bar:Baz.qux')
```

Use `namedtuple` for `RaisesEntry`. No `class` keyword.

-----

## Hard constraints

- Single file: `raises.py`
- No `class` keyword — namedtuples for all data structures
- Pyright programmatic API only — no subprocess, no `--outputjson`
- Pyright is required — fail clearly if absent
- No cross-function propagation: if the target calls another function, do not
  analyse that function's body — not even if it is in the same module
- No exception hierarchy reasoning: `except Exception` does not suppress
  `ValueError` inference — treat each exception type independently
- No dynamic dispatch resolution: ignore `getattr(obj, name)()` patterns

-----

## Validation

Write `test_raises.py` with pytest covering:

1. A function with an explicit `raise ValueError`
   → `builtins.ValueError` in output, step 2
1. A function with `data[key]` where `data: dict`
   → `builtins.KeyError` in output, step 1 (`dict.__getitem__`)
1. A function with `items[i]` where `items: list`
   → `builtins.IndexError` in output, step 1 (`list.__getitem__`)
1. A function with `x / y`
   → `builtins.ZeroDivisionError` in output, step 1 (`int.__truediv__`)
1. A function where the raise is inside an `except` block
   → that exception does NOT appear in output
1. A function that raises a locally-defined exception
   → `module_path.MyError` in output, step 2
1. A function that raises an imported exception
   → fully-qualified name from import source in output, step 2
1. A generator function (`yield` in body)
   → analysis applies normally, callable kind does not affect output
1. CLI invocation: `python raises.py foo.test_module:my_func`
   → output matches expected lines

-----

## Out of scope for milestone 1

- Cross-function or cross-file propagation
- Exception hierarchy reasoning (`except Exception` catching `ValueError`)
- Dynamic dispatch resolution (`getattr`, metaclasses, descriptors)
- C extension inference
