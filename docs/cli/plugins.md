# Plugin Ecosystem

Phase 7 ships a dedicated plugin marketplace:

- urora-se plugin create <name> — scaffold a new extension module.
- urora-se plugin install --spec module:Class --source . — add to registry and config.
- urora-se plugin list — view config and registry entries.
- urora-se plugin remove <name> — uninstall from registry/config.
- urora-se plugin sign <name> — display signature hash.
- urora-se plugin publish <name> — publish manifest to rtifacts/extensions/ for sharing.

The shell /plugin commands allow enabling/disabling specs without leaving the REPL.

