# AccessOwl Skills for Claude

Official AccessOwl skills for [Claude Tag](https://claude.com/docs/claude-tag/overview) (Claude in Slack) and Claude Code, built on the [AccessOwl REST API](https://docs.accessowl.com/api-reference/introduction).

Register this repository once as a plugin marketplace and your team can manage access in plain English: request apps for a new hire, check what someone can use, kick off revocations, and audit access without opening another tool.

> **Status: private / in development.** Will move to the AccessOwl organization before public release.

## Skills

| Skill | Status | What it does |
|---|---|---|
| `request-access` | ✅ | Creates access requests for a user: resolves the application's resources and permissions, checks what the person already has or has pending, handles mandatory resources, and confirms before creating. Requests only, approval stays with your normal process. |
| `request-revocation` | ✅ | Creates revocation requests for a user's access to an application: always establishes who and which app, shows current access, requires a reason, and confirms before creating. Never marks a revocation as completed. |
| `access-gap-fill` | planned | "For every access this colleague has that this user doesn't, create a request", diff two users and request only what's missing. |
| `access-audit` | planned | Ad-hoc access questions: who has what, filtered by department, manager, or role; reconciliation against external lists. |
| `userlist-import-preflight` | planned | Validates and reformats a raw CSV against an app's real resources and permissions before using AccessOwl's userlist importer, and reports exactly which rows can't be mapped. |
| `app-catalog-import` | planned | Creates applications and their full resource/permission structure programmatically; bulk vendor-data updates. |

## Design principles

- **Never guess mandatory resources.** Every skill resolves an application's resources and permissions via the API before creating requests.
- **Confirm before writing.** Skills list planned changes and wait for a go-ahead before creating requests or revocations.
- **Fail gracefully.** The AccessOwl API is enabled per organization; skills explain what to do when the API is not available.

## Setup (once published)

1. In AccessOwl, an Org Admin creates an API token under **Settings → API Tokens**.
2. In Claude Tag's admin settings, add the token as a Bearer credential with `api.accessowl.com` allowlisted, and register this repository as a plugin marketplace.

See the AccessOwl docs for the full guide.
