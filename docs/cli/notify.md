# Notification CLI

Configure outbound channels in configs/notify.yaml and send messages via:

- aurora-se notify slack "Release cut" — logs a Slack event with webhook metadata.
- aurora-se notify email --subject "Incident" "Body" — records an email notification.
- aurora-se notify webhook deploy --payload payload.json — persists a webhook call with payload data.

All notifications are appended to artifacts/notify/log.jsonl for compliance auditing.
