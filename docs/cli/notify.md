# Notification CLI

Configure outbound channels in configs/notify.yaml and send messages via:

- urora-se notify slack "Release cut" — logs a Slack event with webhook metadata.
- urora-se notify email --subject "Incident" "Body" — records an email notification.
- urora-se notify webhook deploy --payload payload.json — persists a webhook call with payload data.

All notifications are appended to rtifacts/notify/log.jsonl for compliance auditing.
