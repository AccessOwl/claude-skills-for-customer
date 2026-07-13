# AccessOwl Skills for Claude

Official AccessOwl skills for [Claude Tag](https://claude.com/docs/claude-tag/overview) (Claude in Slack) and Claude Code, built on the [AccessOwl REST API](https://docs.accessowl.com/api-reference/introduction).

Register this repository once as a plugin marketplace and your team can manage access in plain English: request apps for a new hire, check what someone can use, kick off revocations, and audit access without opening another tool.

> **Status: private / in development.** Will move to the AccessOwl organization before public release.

## Skills

| Skill | Status | What it does |
|---|---|---|
| `request-access` | ✅ | Creates access requests for a user: resolves the application's resources and permissions, checks what the person already has or has pending, handles mandatory resources, and confirms before creating. Requests only, approval stays with your normal process. |
| `request-revocation` | ✅ | Creates revocation requests for a user's access to an application: always establishes who and which app, shows current access, requires a reason, and confirms before creating. Never marks a revocation as completed. |
| `list-access` | ✅ | Lists what a user currently has access to, as an Application/Role table. Read-only, answers exactly what was asked with no extra commentary. |
| `mirror-access` | ✅ | "For every access this colleague has that this user doesn't, create a request": shows the colleague's current access, asks all-or-some, diffs against what the target already has or has pending, confirms, then submits only what's missing. |
| `access-report` | ✅ | Ad-hoc access questions across users and apps: "everyone in Marketing without HubSpot", "contractors with admin permissions", "who has Figma, grouped by role"; reconciles external user lists against AccessOwl and can turn the gap into access requests after confirmation. |
| `userlist-import-preflight` | ✅ | Validates and reformats a raw CSV against an app's real resources and permissions, delivers an import-ready file plus a per-row problem report, and can add missing permissions to the app after explicit confirmation. The import itself runs in AccessOwl (Edit, then Import). |
| `app-catalog-import` | ✅ | Creates applications and their resource/permission structure from lists, spreadsheets, or admin-console screenshots, and bulk-updates vendor details (risk level, data location, auth method, MFA, certificates, review dates). Catalog only, never connects an integration or imports users. |

See [PHRASES.md](PHRASES.md) for the full library of customer phrases per skill.

## Design principles

- **Never guess mandatory resources.** Every skill resolves an application's resources and permissions via the API before creating requests.
- **Confirm before writing.** Skills list planned changes and wait for a go-ahead before creating requests or revocations.
- **Fail gracefully.** The AccessOwl API is enabled per organization; skills explain what to do when the API is not available.

## Setup (once published)

1. In AccessOwl, an Org Admin creates an API token under **Settings → API Tokens**.
2. In Claude Tag's admin settings, add the token as a Bearer credential with `api.accessowl.com` allowlisted, and register this repository as a plugin marketplace.

See the AccessOwl docs for the full guide.
