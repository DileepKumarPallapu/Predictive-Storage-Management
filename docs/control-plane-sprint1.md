# AEGISSTOR Control Plane — Sprint 1

## Scope delivered in this branch

Sprint 1 establishes a strict-authenticated, tenant-scoped Control Plane foundation.

Implemented components:
- Connector registry records with status forced to `NOT_CONFIGURED` on registration.
- No inline secrets in connector configuration; a reference to an external secret manager may be stored.
- Action-definition registry with three built-in definitions:
  - `resource.inspect` — enabled read-only inspection of persisted AEGISSTOR inventory and telemetry.
  - `storage.capacity.plan` — enabled planning calculation requiring fresh, non-synthetic telemetry and separate Administrator approval.
  - `storage.volume.resize` — explicitly disabled until a provider-specific adapter and safety validation exist.
- Persistent action requests, approval decisions, execution records, resource lock schema, audit records and real-time outbox events.
- Strict bearer-token authentication on all new Control Plane HTTP routes and the WebSocket ticket flow.
- Organisation scoping for connector, action and event queries.
- One-time, 60-second WebSocket tickets; raw tickets are not persisted.
- Organisation-scoped WebSocket fanout and event-cursor recovery endpoint.
- Event records are committed in the same database transaction as the corresponding action/audit state; broadcast is attempted only after commit.
- Resource inspection reads persisted database values and reports telemetry provenance.
- Capacity-plan approval is an approval of a proposal only. It does not resize a volume or change infrastructure.

## Explicitly not implemented

- No provider-specific operational connector is registered as connected.
- No physical storage mutation.
- No volume resize.
- No Kubernetes CSI operation.
- No S3 lifecycle execution.
- No privileged Linux action agent.
- No Redis-backed cross-process WebSocket fanout.
- No frontend subscription wiring in this sprint.
- No replay publisher worker for outbox rows after process restart. Clients can recover persisted events through the authenticated event cursor.
- No WORM or external immutable audit storage guarantee.

## Security boundary

The new Control Plane API uses strict bearer authentication and does not use the legacy no-token administrator fallback. Existing legacy routes were not globally reworked in this branch to avoid changing their existing contract without a separate migration and test plan. The existing startup routine also has legacy demo seeding behavior. Production use therefore still requires a separate security/configuration hardening phase before the entire application can be described as production-secure.

## Verification status

The branch contains automated tests for:
- Missing bearer token rejection.
- Operator prohibition on connector registration.
- Connector registration without fake connection status/capabilities.
- Persisted resource inspection and synthetic provenance.
- Capacity plan creation and two-person approval.
- Synthetic telemetry blocking a real capacity plan.
- Single-use ticket response shape.

Tests have not been executed in this environment because a local repository checkout/runtime was unavailable. Do not treat the presence of test files as passing evidence.

## API paths

- `GET /api/v1/control-plane/action-definitions`
- `POST /api/v1/control-plane/connectors` (Administrator)
- `GET /api/v1/control-plane/connectors`
- `GET /api/v1/control-plane/connectors/{connector_id}`
- `POST /api/v1/control-plane/connectors/{connector_id}/health-check` (reports blocked configuration; no adapter is faked)
- `POST /api/v1/control-plane/actions`
- `GET /api/v1/control-plane/actions`
- `GET /api/v1/control-plane/actions/{action_id}`
- `POST /api/v1/control-plane/actions/{action_id}/approve` (Administrator; requester cannot approve own plan)
- `POST /api/v1/control-plane/actions/{action_id}/reject` (Administrator)
- `POST /api/v1/control-plane/actions/{action_id}/execute-read-only` (read-only resource inspection only)
- `GET /api/v1/control-plane/events?after_sequence=N`
- `POST /api/v1/control-plane/realtime/ticket`
- `WS /api/v1/control-plane/ws?ticket=ONE_TIME_TICKET`

## Important operating note

This is a foundation branch, not a production release. The next sprint must add provider-specific read-only adapters, Redis-backed event fanout for multi-instance deployment, frontend WebSocket subscription/reconciliation, worker-based outbox recovery, global strict-auth migration and integration tests against a real authorised storage environment.
