# Workspace Snapshots

The workspace module captures reproducible archives under rtifacts/workspace/:

- urora-se workspace snapshot --tag <tag> — tarball the repo for reproducibility.
- urora-se workspace restore <tag> — restore a stored snapshot.
- urora-se workspace status — summarize inventory and storage footprint.

Snapshots are referenced by the session manager and autopilot artifacts for auditing.

