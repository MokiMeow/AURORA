# Policy CLI

Manage executor/governance policy profiles defined in configs/policy_profiles.yaml:

- aurora-se policy list — enumerate profiles with descriptions.
- aurora-se policy set <profile> — set active profile (stored in configs/policy_active.txt).
- aurora-se policy check --results ci.json — validate CI output using the active profile via PolicyEvaluator.

The shell /policy command mirrors the validation workflow for rapid checks during autopilot runs.
