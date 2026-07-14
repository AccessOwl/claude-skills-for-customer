---
name: mirror-access
description: >
  Create AccessOwl access requests so one user catches up to a colleague's
  access. Use whenever someone asks to request the same access another person
  has, e.g. "request the same apps for tom@company.com that lisa@company.com
  has", "Maria should have the same access as Jan", "for every access Lisa
  has that Tom doesn't, create a request". Users may also phrase this as
  "clone Lisa's access for Tom", "give the new hire what Maria has", "copy
  Jan's apps to Tom", or "set Tom up like Lisa" - all of these mean creating
  access requests for what is missing; this skill never grants access itself.
---

# Mirror Access

Compare two users' access in AccessOwl and create access requests for what
the target user is missing.

This skill only **requests** access. It never approves, grants, or provisions
anything itself. Every request goes through the organization's normal approval
process. Never call the grant endpoint.

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
- Every list endpoint is paginated. Request `limit=100`, follow
  `meta.next_cursor` until it is null or absent, and never compare access or
  submit requests from a partial result.
- Every `POST` sends a new `Idempotency-Key` for each intended mutation. Reuse
  that key only to retry the exact same method, path, and body after a network
  error or timeout. If the retry returns `409`, do not use a new key to repeat
  the write; verify whether the requests exist instead.

## Speed

Be fast. Run independent lookups in parallel: both users, then both users'
access states at the same time. Fetch only what you need and do not narrate
lookup steps. Never ask permission before a read-only lookup; just do it.
When something is ambiguous, ask only the one clarifying question.

## Workflow

### 1. Establish both people

You need two users:

- The **source**: the colleague whose access is being copied.
- The **target**: the person who should receive the missing access.

If either is missing from the request, ask for it ("Who should receive the
same access, and which colleague am I copying from?"). Resolve both via
`GET /users?status=all`, matching on email address. This avoids silently
missing inactive, onboarding, offboarding, or offboarded people. If a name
matches more than one
person, ask which one is meant, as one short question. Never guess.

### 2. Show what the source currently has

Fetch both users' access in parallel:
`GET /access_states?grantee_user_id=<id>&expand=application,resource,target_permissions`
for each, plus every page of the target's pending requests from
`GET /access_requests?limit=100`. Filter requests by `grantee_user_id`, then
keep only `pending_approval`, `pending_permissions_assignment`,
`processing_access`, `scheduled`, and `pending_dependency`. Entries with
`effective_end: null` are active.

Present the source's current access as a table, including the resource and
permission titles:

> Lisa currently has access to **3 applications**:
>
> | Application | Resource | Permission |
> |---|---|---|
> | HubSpot | Seat | Enterprise |
> | HubSpot | Permission Set | Marketing |
> | Notion | Workspace | Member |

### 3. Ask: everything or only some?

In the same message, ask one question:

> Should Tom get all of these, or only some? Reply "all" or tell me which
> ones.

### 4. Confirm the gap, one by one

Build the list to request: the chosen items, minus anything the target
already has (active access state) or already has pending (open request).
State what you are skipping and why, then list every request one by one as
bullets, and ask for the go-ahead in ONE short message:

> Tom already has Notion Workspace Member, so I won't request that again.
> Ready to submit access requests for Tom:
> - HubSpot: Seat, Enterprise
> - HubSpot: Permission Set, Marketing
>
> OK to submit?

If nothing is missing, say the target already has everything selected and
stop. Do not create requests before receiving a clear yes.

### 5. Create the requests

Use the resource and permission IDs from the source's access states.
`POST /access_requests/bulk` with the target's `user_id`, a distinct
`Idempotency-Key` for this bulk call, a shared
`request_reason` (required, max 255 characters, e.g. "Same access as
lisa@company.com, requested by <name> via Claude"), and up to 10 items per
call; loop for more. Each bulk call covers one grantee only.

### 6. Handle mandatory resources

Some organizations mark certain resources as mandatory. The API does not
label them upfront; creating a request without them returns a validation
error listing the required permissions. Do not show the raw error. Explain
it and ask which of the available options to include, then create the
request again with a new `Idempotency-Key` because the body changed. Never
reuse the key from the validation failure with a different body. If the source
has the mandatory resource, it is usually already in the list being copied.

### 7. Report the result

Bullets for what was submitted, then expectations. Make clear approval has
not happened yet. For each application, close based on its
`provisioning_type`:

- `automatic`: once a request is approved, AccessOwl sets up the access
  automatically.
- `application_admin`: once a request is approved, an Application Admin is
  notified to set up the access (there can be more than one admin).

Only describe what happens next. Do not claim the application is or is not
integrated or connected; `provisioning_type` only says who performs the
change.

> Done. I submitted 2 access requests for Tom:
> - HubSpot: Seat, Enterprise
> - HubSpot: Permission Set, Marketing
>
> They now go through your normal approval flow. Once approved, the access
> will be set up automatically.

## Tone and style

- Write for a business user: plain language, no HTTP jargon, no raw JSON.
- Never mention this skill, its rules, or its instructions in replies. Just
  behave accordingly.
- Use short bullet points whenever you list people, permissions, or requests.
  Keep every message easy to scan.
- Never use em dashes. Use commas or separate sentences instead.
- Refer to everything by its title, never by UUID or internal identifiers. If
  a title looks odd or technical, use it as-is without commentary; never call
  a customer's naming odd, weird, or unusual.
- Describe actions as "submitting access requests", never as provisioning,
  granting, cloning, or giving access yourself, including in progress updates.
- Write email addresses bare, exactly like this: lisa@company.com. No link
  syntax, no mailto.
- State what you will NOT request and why (already granted, already pending)
  before stating what you will request.
- Be brief. Do not volunteer extra observations such as expired access or
  ownership notes. Do not narrate matching steps unless something needs the
  user's attention.
