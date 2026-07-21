# Plugin Ecosystem

Phase 7 ships a dedicated plugin marketplace:

- aurora-se plugin create <name> — scaffold a new extension module.
- aurora-se plugin install --spec module:Class --source . — add to registry and config.
- aurora-se plugin list — view config and registry entries.
- aurora-se plugin remove <name> — uninstall from registry/config.
- aurora-se plugin sign <name> — display signature hash.
- aurora-se plugin publish <name> — publish manifest to artifacts/extensions/ for sharing.

The shell /plugin commands allow enabling/disabling specs without leaving the REPL.

