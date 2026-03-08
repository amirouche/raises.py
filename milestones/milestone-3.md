# raises.py — Milestone 3

This milestone extends `raises.py` from Milestone 2. Read the existing
`raises.py` fully before making any changes.

## Goal

Three additions:

1. **Cross-file propagation** — follow calls into other modules where Python
   source is available on disk.
1. **Exception hierarchy reasoning** — delegate to pyright to determine
   whether a `try/except` handler actually catches a given exception.
1. **Narrow dynamic dispatch** — follow `obj.method()` calls when pyright
   resolves the receiver to a union of 3 or fewer concrete types.

-----

## Addition 1 — Cross-file propagation

### What changes

In Milestone 2, propagation stopped at the module boundary. In Milestone 3,
if the target calls a function in an imported module and that module's source
is available on disk, analyse that function using steps 1 and 2 from
Milestone 1, then apply Milestone 2 same-module propagation within that
module.

### Source availability check

Before opening any callee's source, check whether it is available:

```python
import importlib.util

spec = importlib.util.find_spec(module_name)
if spec is None or spec.origin is None:
    # not found — skip, emit nothing
    return []
if spec.origin.endswith(('.so', '.pyd', '.pyc')):
    # C extension or compiled only — skip, emit nothing
    return []
```

If source is available, open `spec.origin` and parse it with `ast.parse`.

### stdlib boundary

If the resolved callee matches a key in `STDLIB_CALLABLE_CONTRACTS`, use the
table and do not open any source file — even if stdlib source happens to be
available on disk. The table is the authoritative answer for stdlib.

### Depth limit

Add a `max_depth` parameter to `raises.analyse()`, default 3. Depth counts
the number of cross-file hops from the original target:

- Depth 0: the target itself (same file as target)
- Depth 1: callees in other modules
- Depth 2: callees of those callees in yet other modules

At `max_depth`, stop following cross-file calls and emit nothing for deeper
callees. Same-module propagation (Milestone 2) does not consume depth — it is
free within any module at any depth level.

### Cycle detection update

The visited set from Milestone 2 now tracks fully-qualified callable names
across modules using the `module:callable` notation. Before analysing any
callee — same-module or cross-file — check the visited set. If already
present, skip silently.

### `via` chain update

The `via` field on `RaisesEntry` becomes a tuple of `module:callable` strings
representing the full propagation path, not just the immediate caller:

```python
RaisesEntry = namedtuple(
    'RaisesEntry',
    ['exception', 'source', 'step', 'via'],
    defaults=[()],   # via defaults to empty tuple for direct findings
)
```

CLI output for a cross-file finding:

```
foo.bar:baz
  builtins.OSError   [pathlib.Path.read_text, step 1,
                      via foo.bar:qux → other.module:helper]
```

-----

## Addition 2 — Exception hierarchy reasoning via pyright

### What changes

Currently `raises.py` treats `try/except` filtering as exact name matching: a
`except ValueError` block suppresses `builtins.ValueError` and nothing else.
This is wrong — `except Exception` also suppresses `ValueError`, and
`except OSError` also suppresses `FileNotFoundError`.

Delegate hierarchy reasoning entirely to pyright. For each `except` handler
in scope of a call site, ask pyright: "does handler type H catch exception
type E?" Use pyright's type narrowing or `issubclass` inference to answer.

Do not implement your own MRO walk. Do not hardcode any hierarchy. Pyright
knows the full inheritance chain — use it.

### Application

Apply hierarchy-aware filtering at every suppression check:

- Step 1 (callable contracts): filter suppressed exceptions using pyright
- Step 2 (explicit raise harvesting): filter suppressed exceptions using pyright
- Propagated exceptions from Milestone 2 and 3: filter at the call site in
  the caller's body using pyright

-----

## Addition 3 — Narrow dynamic dispatch

### What changes

When pyright resolves `obj.method()` and `obj` has a union type, follow the
dispatch if and only if the union contains no `Unknown`, `Any`, or structural
types, and the number of concrete members does not exceed `max_union_width`.

Add `max_union_width` as a keyword argument to `raises.analyse()`, default 3:

```python
def analyse(target, max_depth=3, max_union_width=3):
    ...
```

```python
def is_followable_union(pyright_type, max_union_width) -> bool:
    # return True if the type is a union of concrete types only (no
    # Unknown/Any), and len(members) <= max_union_width
    ...
```

For a followable union, analyse `method` on each concrete type independently,
union their `RaisesEntry` lists, deduplicate by exception name.

For a union that exceeds `max_union_width` but contains no `Unknown` or `Any`
— meaning pyright fully resolved the types but there are more than
`max_union_width` of them — **log a warning** and skip:

```
WARNING foo.bar:baz — skipping dynamic dispatch on obj.save(): receiver is
Union[Foo, Bar, Baz, Qux] (4 concrete types, max_union_width=3). Raise
max_union_width to follow.
```

For a union containing `Unknown` or `Any`, skip silently — the types are not
fully resolved and there is nothing useful to say.

### Example

```python
def process(obj: Union[Foo, Bar]):
    obj.save()   # followable — analyse Foo.save and Bar.save
```

```python
def process(obj: Union[Foo, Bar, Baz, Qux]):
    obj.save()   # wide but concrete — skip with warning
```

```python
def process(obj):  # pyright infers Unknown
    obj.save()   # unknown — skip silently
```

-----

## CLI output update

No new flags required. `max_depth` and `max_union_width` are API-only for
now — the CLI uses defaults of 3 for both. Future `--max-depth=N` and
`--max-union-width=N` flags can expose them.

-----

## Hard constraints (updated)

- Single file: `raises.py`
- No `class` keyword — namedtuples for all data structures
- Pyright programmatic API only — no subprocess, no `--outputjson`
- Pyright is required — fail clearly if absent
- Exception hierarchy reasoning delegated entirely to pyright — no manual MRO
- Dynamic dispatch: follow unions of concrete types up to `max_union_width`
  (default 3, keyword argument); warn when skipping wide concrete unions;
  skip silently on `Unknown` or `Any`
- No C extension inference
- No virtual callees (`__call__` on arbitrary objects, descriptors,
  metaclasses)

-----

## Validation

Extend `test_raises.py` with additional tests:

**Cross-file propagation:**

1. Target calls a function in another module with source available
   → that function's exceptions appear with cross-file `via` path
1. Target calls a function in a C extension (`.so`)
   → no propagation, no error, silent skip
1. Target calls a stdlib function present in `STDLIB_CALLABLE_CONTRACTS`
   → table used, source file not opened even if available
1. Propagation chain exceeds `max_depth=1`
   → deeper callees not followed, output stops at depth 1
1. Cross-file cycle: `foo.bar:baz → other.module:qux → foo.bar:baz`
   → no infinite loop, terminates cleanly

**Exception hierarchy:**

1. Call site inside `except Exception`
   → `builtins.ValueError` from that call does NOT appear (caught by hierarchy)
1. Call site inside `except OSError`
   → `builtins.FileNotFoundError` does NOT appear (subclass of OSError)
1. Call site inside `except OSError`
   → `builtins.ValueError` DOES appear (not a subclass of OSError)

**Dynamic dispatch:**

1. Receiver is `Union[Foo, Bar]` (2 concrete types, within default threshold)
   → exceptions from both `Foo.method` and `Bar.method` appear, deduplicated
1. Receiver is `Union[Foo, Bar, Baz, Qux]` (4 concrete types, exceeds default
   `max_union_width=3`)
   → call site skipped, warning logged, no exceptions emitted
1. Same as 10 but called with `max_union_width=4`
   → call site followed, exceptions from all four types appear
1. Receiver type is `Unknown`
   → call site skipped silently, no warning, no exceptions emitted

-----

## Out of scope permanently

- Exception hierarchy reasoning without pyright (no manual MRO walk)
- Dynamic dispatch on `Unknown` or `Any`
- Virtual callees (`__call__`, descriptors, metaclasses)
- C extension inference
- Packages without Python source
