---
name: list-access
description: >
  List what a user currently has access to in AccessOwl. Use whenever someone
  asks what applications or permissions a person has, e.g. "what does Maria
  have access to?", "list the applications for mjscott@company.com", "does Jan
  have Figma?". Users may also phrase this as "show me Tom's apps", "what can
  Maria use?", or "check Jan's access". This skill is read-only; it never
  creates, changes, or removes anything.
---

# List Access

Answer questions about a user's current access through the AccessOwl REST API.
This skill is read-only.

## API basics

- Base URL: `https://api.accessowl.com/api/v1`. If the configured AccessOwl
  connection points to a different host (for example a sandbox environment),
  use that host with the same `/api/v1` paths.
- Authentication: the AccessOwl API token configured for this environment
  (Bearer token). Do not ask the user for a token.
- If a request returns `401` or redirects to a billing page, the AccessOwl API
  is not enabled for this organization. Tell the user to contact AccessOwl
  support to enable it, and stop.
- On `429`, wait the number of seconds in the `Retry-After` header, then retry.

## Speed

Be fast. This is a read-only lookup, so there is nothing to confirm: resolve
the user, fetch their access, answer. One message. Do not post progress
updates or narrate lookup steps.

## Workflow

### 1. Identify the person

Resolve the user via `GET /users`, matching on email address. If a name was
given and more than one person matches, ask which one is meant. Never guess.

### 2. Fetch their access

`GET /access_states?grantee_user_id=<id>` with permissions expanded. Only
entries with `effective_end: null` are active; show only those. If the
question is about one specific application, filter to it and answer directly
("Yes, Jan has Figma with the Editor permission" or "No, Jan has no active
Figma access").

### 3. Answer with a table

One message. State the person's name, their email as plain text, and the
count, then a table with one row per application:

> Michael J. Scott (mjscott@company.com) currently has access to
> **4 applications**:
>
> | Application | Role |
> |---|---|
> | 1Password | User |
> | ChatGPT | User |
> | Close | User |
> | Internal App | AccessOwl |

- Use the permission titles from AccessOwl as-is. If an application has
  several permissions, list them in the same cell separated by commas.
- If the person has no active access, say so in one sentence.

## Answer only what was asked

Do not volunteer extra observations: no expired access, no ownership notes,
no anomalies, no "one more thing worth flagging", and no closing offers to
dig further. If the user wants expired access or more detail, they will ask.
The only exception: if the question itself cannot be answered cleanly (for
example the person matched two users), ask the one clarifying question needed.

## Tone and style

- Write for a business user: plain language, no HTTP jargon, no raw JSON.
- Never use em dashes. Use commas or separate sentences instead.
- Refer to everything by its title, never by UUID or internal identifiers. If
  a title looks odd or technical, use it as-is without commentary; never call
  a customer's naming odd, weird, or unusual.
- Write email addresses as plain text, not links.
- Be brief. One message with the answer, nothing after the table unless the
  user asked for it.
