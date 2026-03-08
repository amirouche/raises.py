"""raises — Static analysis: what exceptions can this function raise?

Usage:
    raises <target> [<target> ...]

    Target notation: module.path:callable
    where callable is a bare function (baz) or class.method (Baz.qux).

Programmatic API:
    import raises
    result = raises.analyse('foo.bar:baz')
    # returns list of RaisesEntry namedtuples
"""

import ast
import importlib.util
import os
import re
import sys
import tempfile
import warnings
from collections import namedtuple

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

RaisesEntry = namedtuple(
    "RaisesEntry",
    ["exception", "source", "step", "via"],
    defaults=[()],  # via defaults to empty tuple for direct findings
)

# ---------------------------------------------------------------------------
# Callable contracts — keyed on the callable, not the type
# ---------------------------------------------------------------------------

STDLIB_CALLABLE_CONTRACTS = {
    # dict
    "dict.__getitem__": ["builtins.KeyError"],
    "dict.pop": ["builtins.KeyError"],
    "dict.__delitem__": ["builtins.KeyError"],
    # list / tuple / str / bytes
    "list.__getitem__": ["builtins.IndexError"],
    "list.pop": ["builtins.IndexError"],
    "tuple.__getitem__": ["builtins.IndexError"],
    "str.__getitem__": ["builtins.IndexError"],
    "bytes.__getitem__": ["builtins.IndexError"],
    # arithmetic
    "int.__truediv__": ["builtins.ZeroDivisionError"],
    "int.__floordiv__": ["builtins.ZeroDivisionError"],
    "int.__mod__": ["builtins.ZeroDivisionError"],
    "float.__truediv__": ["builtins.ZeroDivisionError"],
    "float.__floordiv__": ["builtins.ZeroDivisionError"],
    "float.__mod__": ["builtins.ZeroDivisionError"],
    # iteration
    "builtins.next": ["builtins.StopIteration"],
    "builtins.iter": ["builtins.TypeError"],
    # type coercion
    "builtins.int": ["builtins.ValueError", "builtins.TypeError"],
    "builtins.float": ["builtins.ValueError", "builtins.TypeError"],
    "builtins.complex": ["builtins.ValueError", "builtins.TypeError"],
    "builtins.bool": ["builtins.TypeError"],
    "builtins.str": [],
    "builtins.bytes": ["builtins.TypeError"],
    # I/O
    "builtins.open": [
        "builtins.FileNotFoundError",
        "builtins.PermissionError",
        "builtins.IsADirectoryError",
        "builtins.OSError",
    ],
    "io.IOBase.read": ["builtins.OSError"],
    "io.IOBase.write": ["builtins.OSError"],
    "io.IOBase.close": ["builtins.OSError"],
    # attributes
    "builtins.getattr": ["builtins.AttributeError"],
    "builtins.delattr": ["builtins.AttributeError"],
    # imports
    "builtins.__import__": ["builtins.ImportError", "builtins.ModuleNotFoundError"],
    "importlib.import_module": ["builtins.ImportError", "builtins.ModuleNotFoundError"],
    # os / path
    "os.remove": [
        "builtins.FileNotFoundError",
        "builtins.PermissionError",
        "builtins.OSError",
    ],
    "os.rename": [
        "builtins.FileNotFoundError",
        "builtins.PermissionError",
        "builtins.OSError",
    ],
    "os.mkdir": [
        "builtins.FileExistsError",
        "builtins.PermissionError",
        "builtins.OSError",
    ],
    "os.makedirs": [
        "builtins.FileExistsError",
        "builtins.PermissionError",
        "builtins.OSError",
    ],
    "os.listdir": [
        "builtins.FileNotFoundError",
        "builtins.PermissionError",
        "builtins.OSError",
    ],
    "os.path.join": [],
    "os.getcwd": ["builtins.OSError"],
    "os.environ.__getitem__": ["builtins.KeyError"],
    "os.environ.get": [],
    # json
    "json.loads": ["json.JSONDecodeError"],
    "json.load": ["json.JSONDecodeError", "builtins.OSError"],
    "json.dumps": ["builtins.TypeError"],
    "json.dump": ["builtins.TypeError", "builtins.OSError"],
    # re
    "re.compile": ["re.error"],
    "re.match": ["re.error"],
    "re.search": ["re.error"],
    "re.findall": ["re.error"],
    "re.sub": ["re.error"],
    # socket
    "socket.socket.connect": [
        "builtins.ConnectionRefusedError",
        "builtins.OSError",
        "builtins.TimeoutError",
    ],
    "socket.socket.bind": ["builtins.OSError"],
    "socket.socket.accept": ["builtins.OSError"],
    "socket.socket.recv": ["builtins.OSError", "builtins.ConnectionResetError"],
    "socket.socket.send": ["builtins.OSError", "builtins.BrokenPipeError"],
    # subprocess
    "subprocess.run": [
        "builtins.FileNotFoundError",
        "subprocess.TimeoutExpired",
        "subprocess.CalledProcessError",
    ],
    "subprocess.check_output": [
        "builtins.FileNotFoundError",
        "subprocess.CalledProcessError",
    ],
    # pathlib
    "pathlib.Path.read_text": [
        "builtins.FileNotFoundError",
        "builtins.PermissionError",
        "builtins.OSError",
    ],
    "pathlib.Path.write_text": ["builtins.PermissionError", "builtins.OSError"],
    "pathlib.Path.mkdir": [
        "builtins.FileExistsError",
        "builtins.PermissionError",
        "builtins.OSError",
    ],
    "pathlib.Path.unlink": [
        "builtins.FileNotFoundError",
        "builtins.PermissionError",
        "builtins.OSError",
    ],
    # urllib
    "urllib.request.urlopen": ["urllib.error.URLError", "urllib.error.HTTPError"],
}

# Builtin exception names that resolve to builtins.<name>
BUILTIN_EXCEPTIONS = {
    "BaseException",
    "Exception",
    "ArithmeticError",
    "AssertionError",
    "AttributeError",
    "BlockingIOError",
    "BrokenPipeError",
    "BufferError",
    "BytesWarning",
    "ChildProcessError",
    "ConnectionAbortedError",
    "ConnectionError",
    "ConnectionRefusedError",
    "ConnectionResetError",
    "DeprecationWarning",
    "EOFError",
    "EnvironmentError",
    "FileExistsError",
    "FileNotFoundError",
    "FloatingPointError",
    "FutureWarning",
    "GeneratorExit",
    "IOError",
    "ImportError",
    "ImportWarning",
    "IndentationError",
    "IndexError",
    "InterruptedError",
    "IsADirectoryError",
    "KeyError",
    "KeyboardInterrupt",
    "LookupError",
    "MemoryError",
    "ModuleNotFoundError",
    "NameError",
    "NotADirectoryError",
    "NotImplementedError",
    "OSError",
    "OverflowError",
    "PendingDeprecationWarning",
    "PermissionError",
    "ProcessLookupError",
    "RecursionError",
    "ReferenceError",
    "ResourceWarning",
    "RuntimeError",
    "RuntimeWarning",
    "StopAsyncIteration",
    "StopIteration",
    "SyntaxError",
    "SyntaxWarning",
    "SystemError",
    "SystemExit",
    "TabError",
    "TimeoutError",
    "TypeError",
    "UnboundLocalError",
    "UnicodeDecodeError",
    "UnicodeEncodeError",
    "UnicodeError",
    "UnicodeTranslateError",
    "UnicodeWarning",
    "UserWarning",
    "ValueError",
    "Warning",
    "ZeroDivisionError",
}

# Map AST BinOp types to dunder method names (only division/modulo)
_BINOP_DUNDERS = {
    ast.Div: "__truediv__",
    ast.FloorDiv: "__floordiv__",
    ast.Mod: "__mod__",
}

# Compiled pyright output patterns
_RE_ERROR_LINE = re.compile(r":(\d+):\d+ - error:")
_RE_TYPE_LINE = re.compile(r':(\d+):\d+ - information: Type of ".+" is "(.+)"')

# ---------------------------------------------------------------------------
# Pyright availability check
# ---------------------------------------------------------------------------


def _ensure_pyright():
    """Import and return pyright.run, or exit with a clear error."""
    try:
        from pyright import run as pyright_run

        return pyright_run
    except ImportError:
        print(
            "Error: pyright is required but not installed.\n"
            "Install it with:  pip install pyright",
            file=sys.stderr,
        )
        sys.exit(1)


# ---------------------------------------------------------------------------
# Target parsing & module resolution
# ---------------------------------------------------------------------------


def _ensure_sys_path():
    """Ensure '' and '.' are in sys.path for local module resolution."""
    if "" not in sys.path:
        sys.path.insert(0, "")
    if "." not in sys.path:
        sys.path.insert(0, ".")


def _parse_target(target):
    """Parse 'module.path:callable' → (module_path, callable_name).

    callable_name is either 'func' or 'Class.method'.
    """
    if ":" not in target:
        print(
            f"Error: invalid target '{target}' — expected module.path:callable",
            file=sys.stderr,
        )
        sys.exit(1)
    module_path, callable_name = target.split(":", 1)
    return module_path, callable_name


def _find_module_file(module_path):
    """Resolve a dotted module path to its .py file."""
    _ensure_sys_path()

    spec = importlib.util.find_spec(module_path)
    if spec is None or spec.origin is None:
        print(f"Error: cannot find module '{module_path}'", file=sys.stderr)
        sys.exit(1)
    return spec.origin


# ---------------------------------------------------------------------------
# AST helpers
# ---------------------------------------------------------------------------


def _find_function_node(tree, callable_name):
    """Find the FunctionDef/AsyncFunctionDef for callable_name in tree.

    callable_name is 'func' or 'Class.method'.
    """
    if "." in callable_name:
        class_name, method_name = callable_name.split(".", 1)
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if item.name == method_name:
                            return item
        return None
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name == callable_name:
                return node
    return None


def _get_handler_exception_names(handler):
    """Extract simple exception names from an except handler's type."""
    names = set()
    if handler.type is None:
        names.add("")  # bare except catches everything
        return names
    if isinstance(handler.type, ast.Name):
        names.add(handler.type.id)
    elif isinstance(handler.type, ast.Tuple):
        for elt in handler.type.elts:
            if isinstance(elt, ast.Name):
                names.add(elt.id)
    elif isinstance(handler.type, ast.Attribute):
        # e.g. except module.Error — use the attribute name
        names.add(handler.type.attr)
    return names


# ---------------------------------------------------------------------------
# Exception hierarchy checking via pyright
# ---------------------------------------------------------------------------


def _run_pyright_on_source(source: str, module_file: str) -> str:
    """Write source to a temp file next to module_file and run pyright.

    Returns pyright's stdout as a string.
    """
    pyright_run = _ensure_pyright()
    module_dir = os.path.dirname(os.path.abspath(module_file))
    fd, temp_path = tempfile.mkstemp(suffix=".py", dir=module_dir)
    try:
        with os.fdopen(fd, "w") as f:
            f.write(source)
        result = pyright_run(temp_path, capture_output=True, text=True)
        stdout = result.stdout
        return stdout if isinstance(stdout, str) else ""
    finally:
        try:
            os.unlink(temp_path)
        except OSError:
            pass


def _fqn_to_annotation(fqn):
    """Convert a fully-qualified name to a valid Python annotation.

    'builtins.KeyError' → 'KeyError'
    'foo.errors.ParseError' → 'foo.errors.ParseError' (needs import)
    """
    if fqn.startswith("builtins."):
        return fqn[len("builtins.") :]
    return fqn


def _check_catches_batch(exception_handler_pairs, module_file):
    """Check whether each (exception_fqn, handler_name) pair is a catch.

    Uses pyright assignability: if ExcType is assignable to HandlerType,
    the handler catches it.

    Returns a set of indices (into exception_handler_pairs) where the handler
    catches the exception.
    """
    if not exception_handler_pairs:
        return set()

    # Build imports and checks
    lines = []
    # Collect all needed imports
    imports_needed = set()
    for exc_fqn, handler_fqn in exception_handler_pairs:
        for fqn in (exc_fqn, handler_fqn):
            if fqn.startswith("builtins."):
                continue  # builtins are always available
            parts = fqn.rsplit(".", 1)
            if len(parts) == 2:
                imports_needed.add((parts[0], parts[1]))

    for mod, name in sorted(imports_needed):
        lines.append(f"from {mod} import {name}")

    lines.append("")

    # For each pair, create an instance and assignment that pyright will flag
    # if the exception type is not assignable to the handler type.
    # Using instances (not annotations) avoids pyright's "unbound" errors.
    marker_lines = {}  # line_number → pair_index
    for i, (exc_fqn, handler_fqn) in enumerate(exception_handler_pairs):
        exc_ann = _fqn_to_annotation(exc_fqn)
        handler_ann = _fqn_to_annotation(handler_fqn)
        var_e = f"_e{i}"
        var_h = f"_h{i}"
        lines.append(f"{var_e} = {exc_ann}()")
        lines.append(f"{var_h}: {handler_ann} = {var_e}  # __CHECK_{i}__")
        marker_lines[len(lines)] = i  # 1-indexed line number

    source = "\n".join(lines) + "\n"

    output = _run_pyright_on_source(source, module_file)

    # Find which lines have errors — those are NON-catches
    error_lines = set()
    for line in output.splitlines():
        m = _RE_ERROR_LINE.search(line)
        if m:
            error_lines.add(int(m.group(1)))

    # A pair is a catch if its assignment line does NOT have an error
    catches = set()
    for line_no, pair_idx in marker_lines.items():
        if line_no not in error_lines:
            catches.add(pair_idx)

    return catches


# ---------------------------------------------------------------------------
# Step 1 — Pyright-assisted callable inference
# ---------------------------------------------------------------------------


def _call_to_contract_key(call_node):
    """Try to map a Call node to a STDLIB_CALLABLE_CONTRACTS key.

    Handles:
        name(...)           → 'builtins.name'    (e.g. open, int, next)
        mod.func(...)       → 'mod.func'         (e.g. json.loads)
        mod.mod2.func(...)  → 'mod.mod2.func'    (e.g. os.path.join)
        obj.method(...)     → None (handled by pyright probes instead)
    """
    func = call_node.func
    if isinstance(func, ast.Name):
        return f"builtins.{func.id}"
    if isinstance(func, ast.Attribute):
        # Build dotted path: json.loads, os.path.join, etc.
        parts = [func.attr]
        node = func.value
        while isinstance(node, ast.Attribute):
            parts.append(node.attr)
            node = node.value
        if isinstance(node, ast.Name):
            parts.append(node.id)
            dotted = ".".join(reversed(parts))
            return dotted
    return None


def _collect_type_probes(func_node):
    """Walk function body, collect nodes that need type resolution.

    Returns a list of dicts with keys:
        kind: 'subscript' | 'binop' | 'call'
        expr: source text for reveal_type()  (subscript/binop only)
        line: original line number
        op: dunder name (subscript/binop) or None (call)
        callable_name: for calls, e.g. 'builtins.open'
        guards: frozenset of exception names handled by enclosing try/except
    """
    probes = []

    def _visit(node, guard_stack):
        if isinstance(node, ast.Try):
            handler_names = set()
            for handler in node.handlers:
                handler_names.update(_get_handler_exception_names(handler))
            new_stack = guard_stack + (frozenset(handler_names),)
            for child in node.body:
                _visit(child, new_stack)
            for handler in node.handlers:
                # Inside except handlers, guard_stack does NOT include this
                # try's handlers (they already caught)
                for child in ast.iter_child_nodes(handler):
                    _visit(child, guard_stack)
            for child in node.orelse:
                _visit(child, guard_stack)
            for child in node.finalbody:
                _visit(child, guard_stack)
            return

        all_guards = frozenset().union(*guard_stack) if guard_stack else frozenset()

        # Subscript — data[key] → need type of data
        if isinstance(node, ast.Subscript):
            probes.append(
                {
                    "kind": "subscript",
                    "expr": ast.unparse(node.value),
                    "line": node.value.lineno,
                    "op": "__getitem__",
                    "callable_name": None,
                    "guards": all_guards,
                }
            )

        # BinOp — x / y → need type of x
        if isinstance(node, ast.BinOp) and type(node.op) in _BINOP_DUNDERS:
            probes.append(
                {
                    "kind": "binop",
                    "expr": ast.unparse(node.left),
                    "line": node.left.lineno,
                    "op": _BINOP_DUNDERS[type(node.op)],
                    "callable_name": None,
                    "guards": all_guards,
                }
            )

        # Call — open(...), next(...), int(...), json.loads(...), etc.
        if isinstance(node, ast.Call):
            contract_key = _call_to_contract_key(node)
            if contract_key is not None and contract_key in STDLIB_CALLABLE_CONTRACTS:
                probes.append(
                    {
                        "kind": "call",
                        "expr": None,
                        "line": (
                            node.func.lineno
                            if hasattr(node.func, "lineno")
                            else node.lineno
                        ),
                        "op": None,
                        "callable_name": contract_key,
                        "guards": all_guards,
                    }
                )

        for child in ast.iter_child_nodes(node):
            _visit(child, guard_stack)

    for child in func_node.body:
        _visit(child, ())

    return probes


def _create_probed_source(source, probes):
    """Insert reveal_type() calls for subscript/binop probes.

    Returns (modified_source, probe_line_map) where probe_line_map maps
    new line numbers (1-indexed) to probe indices.
    """
    # Only subscript and binop probes need reveal_type
    type_probes = [
        (i, p) for i, p in enumerate(probes) if p["kind"] in ("subscript", "binop")
    ]
    if not type_probes:
        return None, {}

    lines = source.splitlines(keepends=True)

    # Group by line number
    by_line = {}
    for probe_idx, probe in type_probes:
        by_line.setdefault(probe["line"], []).append((probe_idx, probe))

    new_lines = []
    probe_line_map = {}

    for orig_lineno, line in enumerate(lines, 1):
        if orig_lineno in by_line:
            indent = len(line) - len(line.lstrip())
            indent_str = line[:indent] if indent > 0 else ""
            for probe_idx, probe in by_line[orig_lineno]:
                reveal_line = (
                    f"{indent_str}reveal_type({probe['expr']})"
                    f"  # __PROBE_{probe_idx}__\n"
                )
                new_lines.append(reveal_line)
                probe_line_map[len(new_lines)] = probe_idx
        new_lines.append(line)

    return "".join(new_lines), probe_line_map


def _extract_base_type(type_str):
    """Extract the base type name from a pyright type string.

    'dict[str, int]' → 'dict'
    'list[Unknown]'  → 'list'
    'int'            → 'int'
    'type[int]'      → 'int'   (for classes used as callables)
    """
    # Handle type[X] — class used as callable
    m = re.match(r"^type\[(\w+)\]$", type_str)
    if m:
        return m.group(1)
    # Handle parameterized types: take everything before '['
    m = re.match(r"^(\w+)", type_str)
    if m:
        return m.group(1)
    return type_str


def _run_pyright_probes(module_file, source, probes):
    """Run pyright on a probed source to resolve types.

    Returns a dict mapping probe_index → base_type_name.
    """
    modified_source, probe_line_map = _create_probed_source(source, probes)
    if modified_source is None:
        return {}

    output = _run_pyright_on_source(modified_source, module_file)

    # Parse reveal_type output lines
    # Format: file.py:LINE:COL - information: Type of "expr" is "TYPE"
    probe_types = {}
    for line in output.splitlines():
        m = _RE_TYPE_LINE.search(line)
        if m:
            lineno = int(m.group(1))
            type_str = m.group(2)
            if lineno in probe_line_map:
                probe_idx = probe_line_map[lineno]
                probe_types[probe_idx] = _extract_base_type(type_str)

    return probe_types


def _step1_pyright_inference(module_path, module_file, source, func_node):
    """Step 1: use pyright to resolve callables and map to contracts.

    Returns a list of (RaisesEntry, guards) pairs for hierarchy-aware filtering.
    """
    probes = _collect_type_probes(func_node)
    if not probes:
        return []

    # Resolve types for subscript/binop probes via pyright
    probe_types = _run_pyright_probes(module_file, source, probes)

    guarded_entries = []  # list of (RaisesEntry, frozenset_of_handler_names)
    for i, probe in enumerate(probes):
        if probe["kind"] == "call":
            callable_name = probe["callable_name"]
        elif i in probe_types:
            base_type = probe_types[i]
            callable_name = f"{base_type}.{probe['op']}"
        else:
            continue

        if callable_name not in STDLIB_CALLABLE_CONTRACTS:
            continue

        exceptions = STDLIB_CALLABLE_CONTRACTS[callable_name]
        for exc in exceptions:
            entry = RaisesEntry(exception=exc, source=callable_name, step=1)
            guarded_entries.append((entry, probe["guards"]))

    return guarded_entries


def _filter_guarded_entries(guarded_entries, module_file, import_map):
    """Filter entries using hierarchy-aware exception checking.

    guarded_entries: list of (RaisesEntry, frozenset_of_handler_names)
    Returns filtered list of RaisesEntry.
    """
    if not guarded_entries:
        return []

    # First pass: quick exact-match filter
    needs_pyright = []
    results = []
    for entry, guards in guarded_entries:
        if not guards:
            results.append(entry)
            continue
        if "" in guards:
            continue  # bare except catches everything
        exc_short = entry.exception.split(".")[-1]
        if exc_short in guards:
            continue  # exact match — caught
        needs_pyright.append((entry, guards))

    if not needs_pyright:
        return results

    # Build batch of (exception_fqn, handler_fqn) pairs
    all_pairs = []
    pair_map = []  # maps pair index to (entry_index, handler)
    for entry_idx, (entry, guards) in enumerate(needs_pyright):
        for h_name in guards:
            if h_name in BUILTIN_EXCEPTIONS:
                h_fqn = f"builtins.{h_name}"
            elif h_name in (import_map or {}):
                h_fqn = import_map[h_name]
            else:
                continue
            pair_map.append(entry_idx)
            all_pairs.append((entry.exception, h_fqn))

    if not all_pairs:
        # No resolvable handlers — all entries pass
        results.extend(e for e, _ in needs_pyright)
        return results

    catches = _check_catches_batch(all_pairs, module_file)

    # Which entry indices are caught?
    caught_entries = {pair_map[i] for i in catches}

    for entry_idx, (entry, _guards) in enumerate(needs_pyright):
        if entry_idx not in caught_entries:
            results.append(entry)

    return results


# ---------------------------------------------------------------------------
# Step 2 — Explicit raise harvesting
# ---------------------------------------------------------------------------


def _build_import_map(tree):
    """Build a map of name → fully-qualified path from import statements."""
    import_map = {}
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            for alias in node.names:
                local_name = alias.asname or alias.name
                import_map[local_name] = f"{module}.{alias.name}"
        elif isinstance(node, ast.Import):
            for alias in node.names:
                local_name = alias.asname or alias.name
                import_map[local_name] = alias.name
    return import_map


def _build_local_defs(tree):
    """Collect names defined at module level (class defs, assignments)."""
    names = set()
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            names.add(node.name)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            names.add(node.name)
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    names.add(target.id)
    return names


def _resolve_exception_name(name, module_path, import_map, local_defs):
    """Resolve an exception name to a fully-qualified path.

    Rule order:
    1. Builtin exceptions → builtins.<name>
    2. Import map → fully qualified from import source
    3. Same-module definition → <module_path>.<name>
    4. Unknown → ?<name>
    """
    if name in BUILTIN_EXCEPTIONS:
        return f"builtins.{name}"
    if name in import_map:
        return import_map[name]
    if name in local_defs:
        return f"{module_path}.{name}"
    return f"?{name}"


def _get_raise_name(node):
    """Extract the exception name from a raise statement's exc attribute.

    Handles:  raise ValueError, raise ValueError(...), raise foo.BarError(...)
    Returns the simple name or None.
    """
    exc = node.exc
    if exc is None:
        return None  # bare raise
    # raise Name or raise Name(...)
    if isinstance(exc, ast.Name):
        return exc.id
    if isinstance(exc, ast.Call):
        if isinstance(exc.func, ast.Name):
            return exc.func.id
        if isinstance(exc.func, ast.Attribute):
            # e.g. raise module.Error() — use the attribute name
            # but we can't fully resolve dotted access here easily
            return exc.func.attr
    if isinstance(exc, ast.Attribute):
        return exc.attr
    return None


def _step2_raise_harvesting(module_path, tree, func_node, import_map=None):
    """Step 2: collect explicit raise statements, skip those in except blocks.

    Returns list of RaisesEntry.
    """
    if import_map is None:
        import_map = _build_import_map(tree)
    local_defs = _build_local_defs(tree)
    entries = []

    def _visit(node, in_except):
        if isinstance(node, ast.Try):
            for child in node.body:
                _visit(child, in_except)
            for handler in node.handlers:
                for child in handler.body:
                    _visit(child, True)
            for child in node.orelse:
                _visit(child, in_except)
            for child in node.finalbody:
                _visit(child, in_except)
            return

        if isinstance(node, ast.Raise) and not in_except:
            name = _get_raise_name(node)
            if name is not None:
                fqn = _resolve_exception_name(name, module_path, import_map, local_defs)
                entries.append(
                    RaisesEntry(
                        exception=fqn,
                        source="explicit raise",
                        step=2,
                    )
                )

        for child in ast.iter_child_nodes(node):
            _visit(child, in_except)

    for child in func_node.body:
        _visit(child, False)

    return entries


# ---------------------------------------------------------------------------
# Same-module propagation helpers
# ---------------------------------------------------------------------------


def _analyse_function_body(module_path, module_file, source, tree, func_node):
    """Run steps 1 and 2 on a function body. Returns list of RaisesEntry."""
    import_map = _build_import_map(tree)

    # Step 1 returns guarded entries for hierarchy-aware filtering
    guarded_entries = _step1_pyright_inference(
        module_path, module_file, source, func_node
    )
    entries = _filter_guarded_entries(guarded_entries, module_file, import_map)

    # Step 2: explicit raise harvesting (already skips except blocks)
    entries.extend(_step2_raise_harvesting(module_path, tree, func_node, import_map))
    return entries


def _collect_call_sites(func_node):
    """Collect call sites in the function body with their guard context.

    Returns list of dicts with keys:
        call_name: simple name of the called function (e.g. 'helper')
        call_attr: for obj.method() calls — (receiver_expr, method_name)
        guards: frozenset of exception names handled by enclosing try/except
        line: line number of the call
    """
    call_sites = []

    def _visit(node, guard_stack):
        if isinstance(node, ast.Try):
            handler_names = set()
            for handler in node.handlers:
                handler_names.update(_get_handler_exception_names(handler))
            new_stack = guard_stack + (frozenset(handler_names),)
            for child in node.body:
                _visit(child, new_stack)
            for handler in node.handlers:
                for child in ast.iter_child_nodes(handler):
                    _visit(child, guard_stack)
            for child in node.orelse:
                _visit(child, guard_stack)
            for child in node.finalbody:
                _visit(child, guard_stack)
            return

        all_guards = frozenset().union(*guard_stack) if guard_stack else frozenset()

        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                call_sites.append(
                    {
                        "call_name": node.func.id,
                        "call_attr": None,
                        "guards": all_guards,
                        "line": node.func.lineno,
                    }
                )
            elif isinstance(node.func, ast.Attribute):
                call_sites.append(
                    {
                        "call_name": None,
                        "call_attr": (ast.unparse(node.func.value), node.func.attr),
                        "guards": all_guards,
                        "line": node.func.lineno,
                    }
                )

        for child in ast.iter_child_nodes(node):
            _visit(child, guard_stack)

    for child in func_node.body:
        _visit(child, ())

    return call_sites


def _find_same_module_functions(tree):
    """Build a dict of function_name → FunctionDef node for module-level functions."""
    funcs = {}
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            funcs[node.name] = node
    return funcs


# ---------------------------------------------------------------------------
# Cross-file source resolution
# ---------------------------------------------------------------------------


def _find_module_source(module_name):
    """Check if a module has Python source available. Returns path or None."""
    _ensure_sys_path()

    try:
        spec = importlib.util.find_spec(module_name)
    except (ModuleNotFoundError, ValueError):
        return None
    if spec is None or spec.origin is None:
        return None
    if not spec.origin.endswith(".py"):
        return None
    return spec.origin



# ---------------------------------------------------------------------------
# Dynamic dispatch helpers
# ---------------------------------------------------------------------------


def _resolve_receiver_type(receiver_expr, func_node, module_file, source):
    """Use pyright to resolve the type of a receiver expression.

    Returns the raw type string from pyright, or None.
    """
    # Create a temp source with reveal_type on the receiver
    lines = source.splitlines(keepends=True)

    # Find the function and insert reveal_type at the top of its body
    insert_line = func_node.body[0].lineno  # 1-indexed
    indent = "    "
    for stmt in func_node.body:
        src_line = lines[stmt.lineno - 1]
        stmt_indent = len(src_line) - len(src_line.lstrip())
        if stmt_indent > 0:
            indent = src_line[:stmt_indent]
            break

    reveal_line = f"{indent}reveal_type({receiver_expr})  # __RECEIVER_PROBE__\n"

    new_lines = list(lines)
    new_lines.insert(insert_line - 1, reveal_line)
    modified_source = "".join(new_lines)

    output = _run_pyright_on_source(modified_source, module_file)

    for line in output.splitlines():
        m = _RE_TYPE_LINE.search(line)
        if m and "__RECEIVER_PROBE__" in line:
            return m.group(2)
        # Also match by line number
        if m and int(m.group(1)) == insert_line:
            return m.group(2)

    return None


def _is_followable_union(type_str, max_union_width):
    """Check if a union type is followable for dynamic dispatch.

    Returns (followable, members, reason) where:
        followable: True if dispatch should be followed
        members: list of concrete type names
        reason: 'ok', 'unknown', or 'too_wide'
    """
    if type_str is None:
        return False, [], "unknown"

    members = [m.strip() for m in type_str.split("|") if m.strip()]
    if not members:
        return False, [], "unknown"

    # Check for Unknown or Any
    for m in members:
        if m in ("Unknown", "Any", "object"):
            return False, members, "unknown"

    if len(members) > max_union_width:
        return False, members, "too_wide"

    return True, members, "ok"


# ---------------------------------------------------------------------------
# Propagation engine (same-module + cross-file)
# ---------------------------------------------------------------------------


def _filter_entries_by_guards(entries, guards, module_file, import_map):
    """Filter propagated entries by guard context using hierarchy-aware check.

    entries: list of RaisesEntry from callee
    guards: frozenset of handler names at the call site
    Returns filtered list.
    """
    if not guards:
        return list(entries)

    guarded = [(e, guards) for e in entries]
    return _filter_guarded_entries(guarded, module_file, import_map)


def _propagate(
    module_path,
    module_file,
    source,
    tree,
    func_node,
    visited,
    via_chain,
    current_depth,
    max_depth,
    max_union_width,
    target_label,
):
    """Propagate exceptions from callees.

    Same-module propagation is free (doesn't consume depth).
    Cross-file propagation consumes one depth level.
    """
    import_map = _build_import_map(tree)
    same_module_funcs = _find_same_module_functions(tree)
    call_sites = _collect_call_sites(func_node)
    propagated = []

    for site in call_sites:
        # --- Simple name calls (e.g. helper(), json.loads is handled by step1) ---
        if site["call_name"] is not None:
            callee_name = site["call_name"]
            callee_fqn = f"{module_path}:{callee_name}"

            # Same-module callee?
            if callee_name in same_module_funcs:
                if callee_fqn in visited:
                    continue
                visited.add(callee_fqn)

                callee_node = same_module_funcs[callee_name]
                callee_entries = _analyse_function_body(
                    module_path, module_file, source, tree, callee_node
                )

                new_via = via_chain + (callee_fqn,)

                filtered = _filter_entries_by_guards(
                    callee_entries, site["guards"], module_file, import_map
                )

                for entry in filtered:
                    propagated.append(entry._replace(via=new_via))
                continue

            # Cross-file callee? Resolve via import map
            if callee_name in import_map:
                imported_fqn = import_map[callee_name]
                # e.g. 'other.module.func_name'
                parts = imported_fqn.rsplit(".", 1)
                if len(parts) == 2:
                    callee_module, callee_func = parts
                    callee_key = f"{callee_module}:{callee_func}"

                    # Check stdlib contracts first
                    if imported_fqn in STDLIB_CALLABLE_CONTRACTS:
                        continue  # handled by step 1

                    if current_depth >= max_depth:
                        continue

                    if callee_key in visited:
                        continue

                    callee_source_path = _find_module_source(callee_module)
                    if callee_source_path is None:
                        continue

                    visited.add(callee_key)
                    try:
                        with open(callee_source_path) as f:
                            callee_source = f.read()
                        callee_tree = ast.parse(callee_source)
                    except (OSError, SyntaxError):
                        continue

                    callee_node = _find_function_node(callee_tree, callee_func)
                    if callee_node is None:
                        continue

                    callee_entries = _analyse_function_body(
                        callee_module,
                        callee_source_path,
                        callee_source,
                        callee_tree,
                        callee_node,
                    )

                    # Also propagate within the callee's module
                    callee_entries.extend(
                        _propagate(
                            callee_module,
                            callee_source_path,
                            callee_source,
                            callee_tree,
                            callee_node,
                            visited,
                            (),
                            current_depth + 1,
                            max_depth,
                            max_union_width,
                            target_label,
                        )
                    )

                    new_via = via_chain + (callee_key,)
                    filtered = _filter_entries_by_guards(
                        callee_entries, site["guards"], module_file, import_map
                    )

                    for entry in filtered:
                        propagated.append(entry._replace(via=new_via + entry.via))

        # --- Attribute calls (e.g. obj.method()) — dynamic dispatch ---
        elif site["call_attr"] is not None:
            receiver_expr, method_name = site["call_attr"]

            # Skip if it looks like a module-level call (already handled by step1)
            contract_key = f"{receiver_expr}.{method_name}"
            if contract_key in STDLIB_CALLABLE_CONTRACTS:
                continue

            # Try to resolve receiver type via pyright
            type_str = _resolve_receiver_type(
                receiver_expr, func_node, module_file, source
            )

            if type_str is None:
                continue

            followable, members, reason = _is_followable_union(
                type_str, max_union_width
            )

            if reason == "unknown":
                continue  # skip silently
            elif reason == "too_wide":
                warnings.warn(
                    f"{target_label} — skipping dynamic dispatch on "
                    f"{receiver_expr}.{method_name}(): receiver is "
                    f"{type_str} ({len(members)} concrete types, "
                    f"max_union_width={max_union_width}). "
                    f"Raise max_union_width to follow.",
                    stacklevel=2,
                )
                continue

            if not followable:
                continue

            # Follow dispatch on each concrete type
            for member_type in members:
                # Extract base type name (strip generics)
                base = _extract_base_type(member_type)

                # Try to find this as class.method in same module
                callee_name = f"{base}.{method_name}"
                callee_fqn = f"{module_path}:{callee_name}"

                if callee_fqn in visited:
                    continue

                callee_node = _find_function_node(tree, callee_name)
                if callee_node is not None:
                    visited.add(callee_fqn)
                    callee_entries = _analyse_function_body(
                        module_path, module_file, source, tree, callee_node
                    )

                    new_via = via_chain + (callee_fqn,)
                    filtered = _filter_entries_by_guards(
                        callee_entries, site["guards"], module_file, import_map
                    )

                    for entry in filtered:
                        propagated.append(entry._replace(via=new_via))
                    continue

                # Try cross-file: resolve the type to a module
                # Look for the type in import_map
                if base in import_map:
                    imported_type_fqn = import_map[base]
                    parts = imported_type_fqn.rsplit(".", 1)
                    if len(parts) == 2:
                        type_module, type_name = parts
                        callee_key = f"{type_module}:{type_name}.{method_name}"

                        if (
                            f"{imported_type_fqn}.{method_name}"
                            in STDLIB_CALLABLE_CONTRACTS
                        ):
                            continue

                        if current_depth >= max_depth:
                            continue

                        if callee_key in visited:
                            continue

                        callee_source_path = _find_module_source(type_module)
                        if callee_source_path is None:
                            continue

                        visited.add(callee_key)
                        try:
                            with open(callee_source_path) as f:
                                callee_source = f.read()
                            callee_tree = ast.parse(callee_source)
                        except (OSError, SyntaxError):
                            continue

                        callee_node = _find_function_node(
                            callee_tree, f"{type_name}.{method_name}"
                        )
                        if callee_node is None:
                            continue

                        callee_entries = _analyse_function_body(
                            type_module,
                            callee_source_path,
                            callee_source,
                            callee_tree,
                            callee_node,
                        )

                        new_via = via_chain + (callee_key,)
                        filtered = _filter_entries_by_guards(
                            callee_entries, site["guards"], module_file, import_map
                        )

                        for entry in filtered:
                            propagated.append(entry._replace(via=new_via + entry.via))

    return propagated


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def analyse(target, max_depth=3, max_union_width=3):
    """Analyse a target and return a list of RaisesEntry namedtuples.

    Target: 'module.path:callable' where callable is 'func' or 'Class.method'.
    max_depth: max cross-file hops (default 3). Same-module is free.
    max_union_width: max union members for dynamic dispatch (default 3).
    """
    _ensure_pyright()  # fail early if pyright is absent

    module_path, callable_name = _parse_target(target)
    module_file = _find_module_file(module_path)
    with open(module_file) as _f:
        source = _f.read()
    tree = ast.parse(source)

    func_node = _find_function_node(tree, callable_name)
    if func_node is None:
        print(
            f"Error: cannot find '{callable_name}' in module '{module_path}'",
            file=sys.stderr,
        )
        sys.exit(1)

    # Steps 1 and 2 on the target function
    entries = _analyse_function_body(module_path, module_file, source, tree, func_node)

    # Propagation (same-module + cross-file, with cycle detection)
    target_fqn = f"{module_path}:{callable_name}"
    visited = {target_fqn}
    entries.extend(
        _propagate(
            module_path,
            module_file,
            source,
            tree,
            func_node,
            visited,
            (),
            0,
            max_depth,
            max_union_width,
            target_fqn,
        )
    )

    # Deduplicate
    seen = set()
    unique = []
    for entry in entries:
        key = (entry.exception, entry.source, entry.step, entry.via)
        if key not in seen:
            seen.add(key)
            unique.append(entry)

    return unique


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _format_output(target, entries):
    """Format entries for CLI output."""
    lines = [target]
    for entry in entries:
        source_label = f"{entry.source}, step {entry.step}"
        if entry.via:
            via_str = " \u2192 ".join(entry.via)
            source_label += f", via {via_str}"
        lines.append(f"  {entry.exception:<25s}[{source_label}]")
    return "\n".join(lines)


def main():
    if len(sys.argv) < 2:
        print("Usage: python raises.py <target> [<target> ...]", file=sys.stderr)
        sys.exit(1)

    targets = sys.argv[1:]
    outputs = []
    for target in targets:
        entries = analyse(target)
        outputs.append(_format_output(target, entries))
    print("\n\n".join(outputs))


if __name__ == "__main__":
    main()
