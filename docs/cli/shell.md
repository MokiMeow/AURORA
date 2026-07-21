# Interactive Shell

The aurora-se shell command offers a REPL with streaming output and the / commands described in plan.md.

## Slash Commands
- /context — display approvals, model, critic state, and active session.
- /model <profile> — switch the default planner route.
- /critic on|off — toggle critic consensus.
- /allow <tool> / /deny <tool> — manage tool permissions.
- /session save <name> / /session load <id> — manage sessions without leaving the shell.
- /workspace snapshot|restore <tag> — capture or restore workspace archives.
- /autopilot <task> — launch a dry-run autopilot cycle.
- /plugin list|enable|disable <spec> — inspect and toggle extensions.
- /logs [--tail N] — tail telemetry logs.
- /reward — show latest reward artifact.
- /policy — run policy validation.
- /help — show command list.
- /quit — exit the REPL.

