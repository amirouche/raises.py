"""Module for cross-file cycle testing."""


def cycle_entry():
    """Calls back into test_module, creating a cross-file cycle."""
    from foo.test_module import calls_cycle_target_back
    calls_cycle_target_back()
    raise TypeError("from cycle_target")
