# Frontend Feature Playbook

## Use when

Changing UI, store flow, WebSocket handling, or player-facing logic.

## Inputs

- linked spec(s)
- impacted pages/components/hooks
- user-visible acceptance criteria

## Steps

1. Read frontend and WS contract specs.
2. Implement typed UI/store changes.
3. Run frontend tests and build.
4. Validate websocket parser compatibility.
5. Register evidence in validation log.

## Required gates

- `cd frontend && npm test`
- `cd frontend && npm run build`
- WS contract parity for event schema changes

## Definition of done

- feature works in typed flow
- tests/build pass
- evidence recorded
- no legacy file deleted
