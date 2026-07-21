# Workspace Snapshots

The workspace module captures reproducible archives under artifacts/workspace/:

- aurora-se workspace snapshot --tag <tag> — tarball the repo for reproducibility.
- aurora-se workspace restore <tag> — restore a stored snapshot.
- aurora-se workspace status — summarize inventory and storage footprint.

Snapshots are referenced by the session manager and autopilot artifacts for auditing.

