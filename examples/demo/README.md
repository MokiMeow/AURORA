# AURORA-SE Demo Monorepo

This sample repository demonstrates how to use AURORA-SE with DeepSeek-R1 to diagnose and fix a simple bug end to end.

## Layout

```
examples/demo/
  pycalc/
    __init__.py
    calc.py         # buggy implementation of add()
  tests/
    test_calc.py    # failing unit test
```

## Scenario

`pycalc.calc.add` incorrectly subtracts numbers. The unit test in `tests/test_calc.py` highlights the regression. We will use AURORA-SE to generate a fix, apply it, and validate the improvement using DeepSeek-R1 as the planner with the critic enabled.

