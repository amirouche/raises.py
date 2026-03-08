# raises.py — Milestone 2

This milestone extends `raises.py` from Milestone 1. Read the existing
`raises.py` fully before making any changes.

## Goal

Add cross-function propagation within the same module. If the target function
calls another function or method defined in the same file, analyse that
callee's body using the same two steps from Milestone 1 and merge its
exceptions into the target's output.

Propagation depth: **one level only**. If `baz` calls `qux` and `qux` calls
`quux`, follow `baz → qux` but not `qux → quux`.

-----

## What changes

### New: hardcoded stdlib callable contracts table

Replace the inline `CALLABLE_CONTRACTS` dict from Milestone 1 with a
comprehensive `STDLIB_CALLABLE_CONTRACTS` table. This table is the
authoritative source for stdlib callables — pyright resolves *what* callable
is being invoked, the table resolves *what it raises*. This avoids relying on
pyright to fully qualify stdlib internals, which it does inconsistently.

```python
STDLIB_CALLABLE_CONTRACTS = {
    # dict
    'dict.__getitem__':          ['builtins.KeyError'],
    'dict.pop':                  ['builtins.KeyError'],
    'dict.__delitem__':          ['builtins.KeyError'],

    # list / tuple / str / bytes
    'list.__getitem__':          ['builtins.IndexError'],
    'list.pop':                  ['builtins.IndexError'],
    'tuple.__getitem__':         ['builtins.IndexError'],
    'str.__getitem__':           ['builtins.IndexError'],
    'bytes.__getitem__':         ['builtins.IndexError'],

    # arithmetic
    'int.__truediv__':           ['builtins.ZeroDivisionError'],
    'int.__floordiv__':          ['builtins.ZeroDivisionError'],
    'int.__mod__':               ['builtins.ZeroDivisionError'],
    'float.__truediv__':         ['builtins.ZeroDivisionError'],
    'float.__floordiv__':        ['builtins.ZeroDivisionError'],
    'float.__mod__':             ['builtins.ZeroDivisionError'],

    # iteration
    'builtins.next':             ['builtins.StopIteration'],
    'builtins.iter':             ['builtins.TypeError'],

    # type coercion
    'builtins.int':              ['builtins.ValueError', 'builtins.TypeError'],
    'builtins.float':            ['builtins.ValueError', 'builtins.TypeError'],
    'builtins.complex':          ['builtins.ValueError', 'builtins.TypeError'],
    'builtins.bool':             ['builtins.TypeError'],
    'builtins.str':              [],
    'builtins.bytes':            ['builtins.TypeError'],

    # I/O
    'builtins.open':             ['builtins.FileNotFoundError',
                                  'builtins.PermissionError',
                                  'builtins.IsADirectoryError',
                                  'builtins.OSError'],
    'io.IOBase.read':            ['builtins.OSError'],
    'io.IOBase.write':           ['builtins.OSError'],
    'io.IOBase.close':           ['builtins.OSError'],

    # attributes
    'builtins.getattr':          ['builtins.AttributeError'],
    'builtins.delattr':          ['builtins.AttributeError'],

    # imports
    'builtins.__import__':       ['builtins.ImportError',
                                  'builtins.ModuleNotFoundError'],
    'importlib.import_module':   ['builtins.ImportError',
                                  'builtins.ModuleNotFoundError'],

    # os / path
    'os.remove':                 ['builtins.FileNotFoundError',
                                  'builtins.PermissionError', 'builtins.OSError'],
    'os.rename':                 ['builtins.FileNotFoundError',
                                  'builtins.PermissionError', 'builtins.OSError'],
    'os.mkdir':                  ['builtins.FileExistsError',
                                  'builtins.PermissionError', 'builtins.OSError'],
    'os.makedirs':               ['builtins.FileExistsError',
                                  'builtins.PermissionError', 'builtins.OSError'],
    'os.listdir':                ['builtins.FileNotFoundError',
                                  'builtins.PermissionError', 'builtins.OSError'],
    'os.path.join':              [],
    'os.getcwd':                 ['builtins.OSError'],
    'os.environ.__getitem__':    ['builtins.KeyError'],
    'os.environ.get':            [],

    # json
    'json.loads':                ['json.JSONDecodeError'],
    'json.load':                 ['json.JSONDecodeError', 'builtins.OSError'],
    'json.dumps':                ['builtins.TypeError'],
    'json.dump':                 ['builtins.TypeError', 'builtins.OSError'],

    # re
    're.compile':                ['re.error'],
    're.match':                  ['re.error'],
    're.search':                 ['re.error'],
    're.findall':                ['re.error'],
    're.sub':                    ['re.error'],

    # socket
    'socket.socket.connect':     ['builtins.ConnectionRefusedError',
                                  'builtins.OSError', 'builtins.TimeoutError'],
    'socket.socket.bind':        ['builtins.OSError'],
    'socket.socket.accept':      ['builtins.OSError'],
    'socket.socket.recv':        ['builtins.OSError',
                                  'builtins.ConnectionResetError'],
    'socket.socket.send':        ['builtins.OSError', 'builtins.BrokenPipeError'],

    # subprocess
    'subprocess.run':            ['builtins.FileNotFoundError',
                                  'subprocess.TimeoutExpired',
                                  'subprocess.CalledProcessError'],
    'subprocess.check_output':   ['builtins.FileNotFoundError',
                                  'subprocess.CalledProcessError'],

    # pathlib
    'pathlib.Path.read_text':    ['builtins.FileNotFoundError',
                                  'builtins.PermissionError', 'builtins.OSError'],
    'pathlib.Path.write_text':   ['builtins.PermissionError', 'builtins.OSError'],
    'pathlib.Path.mkdir':        ['builtins.FileExistsError',
                                  'builtins.PermissionError', 'builtins.OSError'],
    'pathlib.Path.unlink':       ['builtins.FileNotFoundError',
                                  'builtins.PermissionError', 'builtins.OSError'],

    # urllib
    'urllib.request.urlopen':    ['urllib.error.URLError',
                                  'urllib.error.HTTPError'],
}
```

### New: same-module propagation

After running steps 1 and 2 on the target function, identify every call site
in the target body where the callee is a function or method defined in the
same module. Use pyright to resolve the callee's fully-qualified name and
confirm it belongs to the same module.

For each such callee:

1. Run steps 1 and 2 on the callee's body (exactly as for the original target).
1. Merge the callee's `RaisesEntry` list into the target's results, adding a
   `via` field to each entry indicating the propagation path.
1. Filter out any exception already handled by a `try/except` wrapping the
   call site in the target body.

Update `RaisesEntry` to carry an optional `via` field:

```python
RaisesEntry = namedtuple(
    'RaisesEntry',
    ['exception', 'source', 'step', 'via'],
    defaults=[None],   # via defaults to None for direct findings
)
```

### New: cycle detection

Before analysing a callee, check whether it is already in the current
propagation stack. If yes, skip it and emit no entries for that callee — do
not loop. A simple `set` of already-visited callable names is sufficient.

-----

## CLI output update

Show propagated exceptions with their path:

```
foo.bar:baz
  builtins.KeyError        [dict.__getitem__, step 1]
  builtins.ValueError      [explicit raise, step 2]
  builtins.OSError         [pathlib.Path.read_text, step 1, via foo.bar:qux]
  foo.bar.ParseError       [explicit raise, step 2, via foo.bar:qux]
```

-----

## Hard constraints (unchanged from Milestone 1)

- Single file: `raises.py`
- No `class` keyword — namedtuples for all data structures
- Pyright programmatic API only — no subprocess, no `--outputjson`
- Pyright is required — fail clearly if absent
- No cross-file propagation: same-module callees only
- No exception hierarchy reasoning
- No dynamic dispatch resolution

-----

## Validation

Extend `test_raises.py` with additional tests:

1. Target calls a same-module helper that has an explicit `raise`
   → helper's exception appears in target output with `via` annotation
1. Target calls a same-module helper that has a dict subscript
   → `builtins.KeyError` appears with `via` annotation
1. Target calls a same-module helper, but the call is inside a
   `try/except KeyError` block
   → `builtins.KeyError` from helper does NOT appear in target output
1. Mutual recursion: `baz` calls `qux`, `qux` calls `baz`
   → no infinite loop, output terminates, cycle is silently skipped
1. Target calls a function from an imported module (not same-module)
   → that function's body is NOT analysed, no propagation occurs
1. Target calls a stdlib function (`json.loads`)
   → `json.JSONDecodeError` appears via `STDLIB_CALLABLE_CONTRACTS`, not
   via propagation

-----

## Out of scope for Milestone 2

- Cross-file propagation (callees in other modules)
- Exception hierarchy reasoning (`except Exception` catching `ValueError`)
- Dynamic dispatch resolution (`getattr`, metaclasses, descriptors)
- Propagation beyond one level deep (`baz → qux → quux`)
- Coroutine-specific propagation across `await` boundaries
- C extension inference
