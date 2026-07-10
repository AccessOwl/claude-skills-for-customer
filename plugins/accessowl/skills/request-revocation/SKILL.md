---
name: request-revocation
description: >
  Revoke a user's access to an application via AccessOwl. Use whenever someone
  asks to revoke, remove, or take away access, e.g. "remove Jan's Figma
  access", "revoke the HubSpot seat for tom@company.com", "Jan left, take away
  his Salesforce access".
---

# Request Revocation

Create access revocations in AccessOwl through its REST API. A revocation is a
real action: for integrated applications it triggers deprovisioning, so always
confirm before creating one.

## API basics

- Base URL: `https://api.accessowl.com/api/v1`
- Authentication: the AccessOwl API token configured for this environment
  (Bearer token). Do not ask the user for a token.
- If a request returns `401` or redirects to a billing page, the AccessOwl API
  is not enabled for this organization. Tell the user to contact AccessOwl
  support to enable it, and stop.
- On `429`, wait the number of seconds in the `Retry-After` header, then retry.

## Workflow

### 1. Establish who and which application

You always need both: the **user** and the **application**. If either is
missing from the request, ask for it before doing anything else. Resolve the
user via `GET /users` (match on email; ask if a name is ambiguous) and the
application via `GET /applications?title_like=<name>` (ask if several match).

### 2. Show what the person currently has

Fetch `GET /access_states?grantee_user_id=<id>&application_id=<id>`. Entries
with `effective_end: null` are active. Present them by title:

> Jan currently has in HubSpot: Enterprise seat, Sales permission set.

If the person has no active access to that application, say so and stop.

### 3. Ask what to revoke, and why

Ask whether to revoke everything listed or only specific entries, unless the
user already said. A `reason` is required for every revocation (max 255
characters); ask for one if none was given, or use a short factual reason
such as "Requested by <name> via Claude".

### 4. Confirm before creating

Summarize the person, the application, and each access to be revoked, by
title. Ask for a clear go-ahead. Do not create revocations before receiving it.

### 5. Create the revocations

For each selected access state: `POST /access_revocations` with
`access_state_id` and `reason`.

### 6. Report the result and set expectations

- For applications with an active integration, AccessOwl deprovisions the
  access automatically.
- For applications without an integration, AccessOwl notifies the Application
  Admin, who removes the access in the application. The revocation stays in
  progress until they confirm it, so it will not show as completed
  immediately. Say this plainly so the user isn't surprised:

> I created 2 revocations for Jan's HubSpot access. HubSpot is not an
> integrated application in your setup, so your Application Admin has been
> notified to remove the access and will confirm once done.

## Tone and style

- Write for a business user: plain language, no HTTP jargon, no raw JSON.
- Refer to everything by its title, never by UUID.
- Revocations are sensitive. Be precise about what will happen and when, and
  never revoke more than what was confirmed.
