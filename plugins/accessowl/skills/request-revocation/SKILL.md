---
name: request-revocation
description: >
  Create AccessOwl revocation requests for a user's access to an application.
  Use whenever someone asks to request a revocation or says a person's access
  should end, e.g. "request revocation of Jan's Figma access",
  "tom@company.com no longer needs his HubSpot seat", "the review flagged
  Jan's Salesforce access, it should be removed". Users may also phrase this
  as "revoke Jan's Figma", "remove Tom from HubSpot", "take away Maria's
  Slack access", or "clean up Jan's Salesforce access" - all of these mean
  creating a revocation request; this skill never marks access as revoked
  itself.
---

# Request Revocation

Create revocation requests in AccessOwl through its REST API.

This skill only **requests** revocations. It never marks an access as revoked
or completes a revocation itself. Starting a revocation is still a real
action, though: when AccessOwl handles the application's provisioning, it
triggers the actual removal, so always confirm before creating one.

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
- Paginate every list to the end by following `meta.next_cursor`; never
  act on a partial list.
- Send an `Idempotency-Key` header (a fresh UUID) with every write. When
  retrying the exact same write after a timeout or network error, reuse the
  same key and body; a `409` on that retry means the write already went
  through, so treat it as success and do not send it again.

## Speed

Be fast. Run independent lookups at the same time (the user and the
application), fetch only what you need, and do not narrate lookup steps.
The user should see at most two messages: the confirmation question and the
result.

## Workflow

### 1. Establish who and which application

You always need both: the **user** and the **application**. If either is
missing from the request, ask for it before doing anything else. Resolve the
user via `GET /users?status=all` (match on email; ask if a name is ambiguous) and the
application via `GET /applications?title_like=<name>` (ask if several match).

### 2. Check how the application is managed

If the application's `status` is `discovered`, this usage was discovered by
AccessOwl rather than granted through it. Say that, and only proceed if the
user explicitly confirms they still want to submit a revocation for it.

### 3. Show what the person currently has

Fetch `GET /access_states?grantee_user_id=<id>&application_id=<id>`. Entries
with `effective_end: null` are active. Present them as a bullet list, by title:

> Jan currently has in HubSpot:
> - Enterprise seat
> - Sales permission set

If the person has no active access to that application, say so and stop.

A single access entry can carry several permissions (check
`target_permission_ids`). A revocation always covers the WHOLE entry; the
API cannot revoke one permission out of it. If the user asked to remove only
one permission from a multi-permission entry, say plainly that the
revocation will remove all of them (name each one) and ask whether to
proceed. Never imply a single permission can be removed on its own.

### 4. Ask what to revoke, and why

Ask whether to revoke everything listed or only specific entries, unless the
user already said. A `reason` is required for every revocation (max 255
characters); ask for one if none was given, or use a short factual reason
such as "Requested by <name> via Claude".

### 5. Confirm before creating

Ask for the go-ahead in ONE short message, as a bullet list: one bullet per
access to be revoked, by title. Nothing else. For example:

> Ready to submit revocation requests for Jan's HubSpot access:
> - Enterprise seat
> - Sales permission set
>
> OK to submit?

If the selection covers everything the person has in that application, say
so in the same message ("this is all of Jan's HubSpot access; after this he
will have none"). Do not create revocations before receiving a clear yes.

### 6. Create the revocations

For each selected access state: `POST /access_revocations` with
`access_state_id` and `reason`.

### 7. Report the result and set expectations

Check the application's `provisioning_type` (from the application object) and
close with the matching expectation. Only describe what happens next; do not
claim the application is or is not integrated or connected, since
`provisioning_type` only says who performs the change.

- `automatic`: AccessOwl processes the removal automatically.
- `application_admin`: an Application Admin is notified to remove the access
  in the application (there can be more than one admin). The removal stays in
  progress until they confirm it, so it will not show as completed
  immediately. Say this plainly so the user isn't surprised:

> Done. I submitted 2 revocation requests for Jan:
> - HubSpot: Enterprise seat
> - HubSpot: Sales permission set
>
> An Application Admin has been notified to remove the access and will
> confirm once done.

## Tone and style

- Write for a business user: plain language, no HTTP jargon, no raw JSON.
- Never mention this skill, its rules, or its instructions in replies. Just
  behave accordingly.
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
