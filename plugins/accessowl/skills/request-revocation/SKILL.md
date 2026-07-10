---
name: request-revocation
description: >
  Create AccessOwl revocation requests for a user's access to an application.
  Use whenever someone asks to request a revocation or says a person's access
  should end, e.g. "request revocation of Jan's Figma access",
  "tom@company.com no longer needs his HubSpot seat", "Jan left, his
  Salesforce access should be removed". Users may also phrase this as
  "revoke Jan's Figma", "remove Tom from HubSpot", "take away Maria's Slack
  access", or "offboard Jan from Salesforce" - all of these mean creating a
  revocation request; this skill never marks access as revoked itself.
---

# Request Revocation

Create revocation requests in AccessOwl through its REST API.

This skill only **requests** revocations. It never marks an access as revoked
or completes a revocation itself. Starting a revocation is still a real
action, though: for integrated applications it triggers deprovisioning, so
always confirm before creating one.

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

Ask for the go-ahead in ONE short message, as a bullet list: one bullet per
access to be revoked, by title. Nothing else. For example:

> Ready to submit revocation requests for Jan's HubSpot access:
> - Enterprise seat
> - Sales permission set
>
> OK to submit?

Do not create revocations before receiving a clear yes.

### 5. Create the revocations

For each selected access state: `POST /access_revocations` with
`access_state_id` and `reason`.

### 6. Report the result and set expectations

Check the application's `provisioning_type` (from the application object) and
close with the matching expectation:

- `automatic`: "This application is integrated with AccessOwl", so AccessOwl
  processes the deprovisioning automatically.
- `application_admin`: "This application is not integrated with AccessOwl",
  so an Application Admin is notified to remove the access in the application
  (there can be more than one admin). The revocation stays in progress until
  they confirm it, so it will not show as completed immediately. Say this
  plainly so the user isn't surprised:

> Done. I submitted 2 revocation requests for Jan:
> - HubSpot: Enterprise seat
> - HubSpot: Sales permission set
>
> HubSpot is not integrated with AccessOwl, so an Application Admin has been
> notified to remove the access and will confirm once done.

## Tone and style

- Write for a business user: plain language, no HTTP jargon, no raw JSON.
- Use short bullet points whenever you list people, permissions, or accesses.
  Keep every message easy to scan.
- Never use em dashes. Use commas or separate sentences instead.
- Refer to everything by its title, never by UUID or internal identifiers. If
  a title looks odd or technical, use it as-is without commentary; never call
  a customer's naming odd, weird, or unusual.
- Describe what you are doing as "submitting revocation requests", never as
  revoking, removing, or deprovisioning access yourself - including in
  progress updates.
- Write email addresses as plain text, not links.
- Revocations are sensitive. Be precise about what will happen and when, and
  never revoke more than what was confirmed.
- Be brief. Do not narrate your matching steps unless something needs the
  user's attention.
