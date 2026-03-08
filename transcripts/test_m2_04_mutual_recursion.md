# M2 Test 4: test_m2_mutual_recursion

## Given

```python
# foo/test_module.py
def mutual_a():
    mutual_b()
    raise ValueError("from a")

def mutual_b():
    mutual_a()
    raise TypeError("from b")
```

Two functions that call each other (mutual recursion).

## Executed

```python
result = raises.analyse('foo.test_module:mutual_a')
```

## Expected

- Terminates without hanging (no infinite loop)
- `builtins.ValueError` in results (direct from mutual_a, step 2)
- `builtins.TypeError` in results (propagated from mutual_b, via annotation)

## Why

Cycle detection prevents infinite recursion. When analysing `mutual_a`:
1. `mutual_a` is added to the visited set as `foo.test_module:mutual_a`
2. Propagation finds `mutual_b()` call → analyses mutual_b
3. mutual_b's analysis finds `mutual_a()` call → but `foo.test_module:mutual_a`
   is already in visited → skip silently
4. mutual_b's own `raise TypeError` is collected and propagated back to mutual_a
   with a via annotation
