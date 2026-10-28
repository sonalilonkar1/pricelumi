# Staging and logging plan

**Status:** Proposed for W1-23 review. No staging deployment or logging changes have been implemented.

Staging is a shared test environment where the team can check the frontend and
backend together before release. Use sample data only.

## Deployment approach

Start with one frontend, one backend and a PostgreSQL database. Keep Redis deferred.
The hosting platform and deployment method still need confirmation. Keep the first
deployment simple; automated deployment can follow after the initial setup works.

1. Confirm the hosting platform, access owner and approved budget with Sonali and the PMs.
2. Use Satya's backend and Rayyan's frontend files to confirm build/start commands,
   ports and required settings. Add the application Dockerfiles where needed.
3. Provision a separate staging database with persistent storage and restricted access.
   Agree on migrations with Satya before adding application tables.
4. Configure secrets in the hosting platform, deploy the backend and frontend,
   and record their URLs and deployed commit below.
5. Run the checks in this document and share the result before inviting team testing.

Do not reuse developers' local passwords or treat the local Compose setup as a
finished staging configuration. Use HTTPS and restrict staging access to the team
before sharing it. Confirm a backup and restore approach before storing important data.

## Settings to confirm

| Setting | Purpose |
| --- | --- |
| Backend database connection | Staging host, port, database, application user and password; confirm the environment variable names with Satya |
| Frontend API URL | The address the frontend uses to reach the backend; confirm the variable name and whether it is set at build time |
| Allowed frontend origin | The exact frontend URL the backend accepts browser requests from (CORS) |
| Application secrets | Configure only the keys needed for the deployed features; keep mock integrations until approved access is available |

Keep secrets out of Git, browser-visible frontend settings and logs. Give the
backend an application database account rather than an administrator account.
Database encryption and network settings should follow the selected provider's setup.

## Health checks

Agree on the readiness route and response with Satya before implementation.

| Check | Proposed behaviour |
| --- | --- |
| `GET /health` | Return HTTP 200 when the backend process can respond. Keep it independent of PostgreSQL, as agreed with Satya. |
| Readiness check (route to confirm) | Return HTTP 200 when the backend can serve its current API; return HTTP 503 when a required dependency is unavailable. Check PostgreSQL only once the API needs it. |

Keep responses small and generic. Do not expose connection strings, credentials or
internal error details. Health probes should not call paid model APIs or retailer tools.

## Request logging

Propose one JSON log entry per completed backend request, written to standard
output so the hosting platform can collect it. JSON keeps each field separate and
makes logs easier to search.

Record only:

- UTC timestamp and severity (`INFO`, `WARNING` or `ERROR`).
- A server-generated request ID, returned in `X-Request-ID` so a caller can report it.
- HTTP method, route template, response status and duration in milliseconds.
- A generic error code for failed requests, where available.

Use a route template such as `/api/shopping-runs/{run_id}` rather than the full URL
or an actual customer/run identifier. For unmatched routes, log a generic label.
Do not log query strings, request/response bodies, shopping queries, authorization
headers, cookies, API keys, passwords or customer information. Do not log raw
exception messages that may contain these values.

Satya and Arjun should agree where this is implemented in the backend. Use the same
request ID in related service logs when practical. Confirm who can view staging
logs and how long they are retained after choosing the platform.

## Verification before sharing staging

| Check | Expected result |
| --- | --- |
| Frontend URL | Loads over HTTPS for an authorized team member |
| Backend health | `/health` returns HTTP 200 |
| Readiness, once implemented | Returns 200 when ready and 503 when a required dependency is unavailable |
| Frontend to backend | A sample shopping request reaches the backend and returns the expected mock result |
| Database, once integrated | Backend uses its application account and approved migrations complete successfully |
| Request logs | Success and failure requests have request IDs, status and timing; a dummy sensitive value in a test request does not appear in logs |
| Access and configuration | Team access restrictions work, the database is not publicly accessible, and secrets are absent from browser assets and logs |

Run dependency-failure checks in an isolated test environment, not during shared
team testing. For deployment problems, keep the previous working commit available
for redeployment. Database migration rollback needs a separate plan agreed with Satya.

## Deployment record

| Item | Current status |
| --- | --- |
| Hosting platform and access owner | Pending confirmation |
| Frontend and backend build/start commands | Pending application files |
| Frontend URL / backend URL | Not deployed |
| Deployed commit and verification date | Not deployed |
| Logging and readiness implementation | Pending backend integration |

While hosting or application files are unavailable, use the validated local
PostgreSQL setup and run application skeletons locally once received. This is the
temporary fallback, not a completed staging deployment. Update this record with
the blocker, fallback and next action if staging remains unavailable.
