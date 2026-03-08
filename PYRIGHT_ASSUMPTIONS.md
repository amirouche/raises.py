# Pyright Assumptions

This document lists every behavior of pyright that `raises.py` depends on.
If pyright changes any of these behaviors, tests may break. Each assumption
includes how to verify it independently.

---

## 1. `reveal_type()` output format

**Assumption:** When pyright encounters `reveal_type(expr)`, it emits an
information diagnostic with the format:

```
<file>:<line>:<col> - information: Type of "<expr>" is "<type>"
```

**Used by:** `_run_pyright_probes()`, `_resolve_receiver_type()`

**Regex:** `:(\d+):\d+ - information: Type of ".+" is "(.+)"`

**Verification:**
```python
# file: /tmp/test.py
x: int = 42
reveal_type(x)
```
Expected output contains: `Type of "x" is "int"`

---

## 2. Type representation for parameterized types

**Assumption:** Pyright represents parameterized types as `base[params]`:
- `dict[str, int]` for typed dicts
- `list[int]` for typed lists
- `type[Foo]` for class objects used as callables

**Used by:** `_extract_base_type()` — extracts the base name before `[`.

**Verification:**
```python
x: dict[str, int] = {}
reveal_type(x)
```
Expected: `Type of "x" is "dict[str, int]"`

---

## 3. Union type syntax

**Assumption:** Pyright represents union types using `|` syntax:
`Foo | Bar | Baz` (not `Union[Foo, Bar, Baz]`).

**Used by:** `_parse_union_type()` — splits on `|` to get members.

**Verification:**
```python
from typing import Union
x: Union[int, str] = 42
reveal_type(x)
```
Expected: `Type of "x" is "int | str"`

---

## 4. Unknown/Any type representation

**Assumption:** When pyright cannot resolve a type, it reports it as
`Unknown` (in strict mode) or the inferred type. The strings `Unknown`
and `Any` appear literally in the type output.

**Used by:** `_is_followable_union()` — checks for `Unknown` and `Any`
members in unions to decide whether dynamic dispatch is safe.

**Verification:**
```python
def f(x):
    reveal_type(x)
```
Expected: Contains `Unknown` in the type string (strict mode).

---

## 5. Type assignability for exception hierarchy

**Assumption:** Pyright checks type assignability on variable assignments.
If `ExcType` is a subclass of `HandlerType`, then:
```python
_e = ExcType()
_h: HandlerType = _e  # No error
```
If NOT a subclass:
```python
_e = ExcType()
_h: HandlerType = _e  # Error: Type "ExcType" is not assignable to "HandlerType"
```

**Used by:** `_check_catches_batch()` — determines whether an except
handler catches a given exception type.

**Important:** We use instance creation (`ExcType()`) rather than type
annotations (`_e: ExcType`) because pyright reports "unbound" errors for
annotated-but-not-assigned variables.

**Error format:** `:(\d+):\d+ - error:` — any error on the assignment line
means the types are NOT compatible.

**Verification:**
```python
_e0 = KeyError()
_h0: Exception = _e0    # No error (KeyError is subclass of Exception)

_e1 = KeyError()
_h1: OSError = _e1      # Error (KeyError is not subclass of OSError)
```

---

## 6. `pyright.run()` API

**Assumption:** The `pyright` Python package exposes a `run()` function
that accepts a file path and `capture_output=True, text=True` kwargs,
returning a result object with `.stdout` containing diagnostic output.

**Used by:** `_ensure_pyright()`, `_run_pyright_probes()`,
`_check_catches_batch()`, `_resolve_receiver_type()`

**Verification:**
```python
from pyright import run
result = run('/tmp/test.py', capture_output=True, text=True)
assert hasattr(result, 'stdout')
```

---

## 7. Temp file in same directory resolves imports

**Assumption:** When pyright analyses a temp file placed in the same
directory as the target module, it resolves relative imports and
module-level imports correctly, as if the temp file were the actual module.

**Used by:** `_run_pyright_probes()`, `_check_catches_batch()`,
`_resolve_receiver_type()`

**Verification:** Place a temp `.py` file next to a module that imports
from sibling modules. Run pyright on the temp file — imports should resolve.

---

## 8. Error diagnostic format

**Assumption:** Pyright error diagnostics follow the format:
```
<file>:<line>:<col> - error: <message> (<rule>)
```

**Used by:** `_check_catches_batch()` — regex `:(\d+):\d+ - error:`

**Verification:**
```python
x: int = "hello"
```
Expected output contains: `- error: Type "str" is not assignable to declared type "int"`

---

## 9. `reveal_type` insertion does not break surrounding code

**Assumption:** Inserting `reveal_type(expr)` statements before lines in
the source does not change pyright's ability to type-check the surrounding
code. The inserted lines shift line numbers but do not affect scope or
type inference.

**Used by:** `_create_probed_source()`, `_resolve_receiver_type()`

---

## 10. Exception constructors accept no required args

**Assumption:** All builtin exception classes can be instantiated with no
arguments: `KeyError()`, `ValueError()`, `OSError()`, etc. Pyright knows
this and does not report errors for `ExcType()` with no args.

**Used by:** `_check_catches_batch()` — creates instances like `_e0 = KeyError()`

**Verification:** Pyright should not error on `x = KeyError()`.
