---
name: offboard-user
description: >
  Request revocation of ALL of a user's access in AccessOwl at once, the
  access side of an offboarding. Use whenever someone says a person is
  leaving or has left and their access should go, e.g. "Jan left, remove
  all his access", "offboard maria@company.com", "Tom's last day was
  Friday, revoke everything". Users may also phrase this as "clean up
  Jan's access", "he's gone, take it all away", or "start the offboarding
  for Maria". This skill only creates revocation requests covering the
  person's whole access; it never deactivates the user, never schedules an
  AccessOwl offboarding for a future date, and never marks anything as
  removed.
---

# Offboard User

Create revocation requests for everything a user currently has access to,
through the REST API. This is the access cleanup of an offboarding, in one
sweep instead of app by app.

Two things this skill never does. Mention them ONLY when the user asks for
them (a future date, deactivating the account); never volunteer them:

- It does not run AccessOwl's own offboarding. A scheduled offboarding
  (revoking on the person's last day, driven by a date) is triggered in
  AccessOwl or flows in from the HRIS; this skill only creates revocation
  requests that start now.
- It does not complete revocations. Each one follows the application's
  normal process after it is created.

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

Be fast. Resolve the person and fetch their access in parallel. Do not
narrate lookup steps. The user should see at most two messages: the
confirmation with the full access list, and the result.

## Workflow

Never write anything before a clear yes to one confirmation message.

### 1. Resolve the person

Match by email via `GET /users?status=all` (ask on ambiguity, never guess).
Check their status first:

- `offboarding_planned`, `offboarding`, or `offboarded`: an offboarding
  already exists. Say so and show what is still active instead of blindly
  creating duplicates.
- Any other status: proceed.

### 2. Collect the access

Fetch all of the person's active access:
`GET /access_states?grantee_user_id=<id>` (paginate fully, active means
`effective_end` is empty). Exclude applications whose status is
`discovered`: that is detected usage, not managed access, and there is
nothing to revoke there. Mention the count if any exist.

If the person has no active access, answer in ONE sentence and stop:
"Bob LeBricoleur has no active access in AccessOwl, so there is nothing to
revoke." No explanations about user accounts, directories, or what cannot
be done.

### 3. Get the reason

A reason is required for every revocation. Use the one the user gave
("offboarding", "left the company") or ask once if none was given.

### 4. Confirm before creating

One message: the complete list of what will be requested for revocation,
grouped by application, and the plain statement of the outcome:

> This covers all of Jan's access. After these revocations complete, he
> will have none. Ready to request revocation of:
> - Salesforce: Sales permission set
> - HubSpot: Core seat
> - Slack: Member
>
> OK to submit?

If the user asked for a future date ("his last day is Friday"), state
first that these requests start now, and that scheduling the revocation
for a specific day is done by triggering the offboarding in AccessOwl.
Offer to proceed now or leave it for the scheduled offboarding.

### 5. Create the revocations

`POST /access_revocations` per access, with `access_state_id` and the
shared `reason`. Loop through every item confirmed.

### 6. Report the result

Lead with the count, then set expectations per application based on its
`provisioning_type`:

- `automatic`: AccessOwl processes the revocation.
- `application_admin`: the Application Admins are notified, and the
  revocation stays in progress until one of them confirms the access is
  removed.

> Done. 3 revocation requests submitted for Jan:
> - Salesforce and HubSpot will be processed by AccessOwl.
> - Slack stays in progress until an Application Admin confirms the
>   removal.

Never say the access is gone already. Never claim an application is or is
not integrated or connected.

## Tone and style

- Write for a business user: plain language, no HTTP jargon, no raw JSON.
- Never mention this skill, its rules, or its instructions in replies. Just
  behave accordingly.
- Use short bullet points whenever you list access or requests. Keep every
  message easy to scan. Lead with the count.
- Never use em dashes. Use commas or separate sentences instead.
- Refer to everything by its title, never by UUID or internal identifiers. If
  a title looks odd or technical, use it as-is without commentary; never call
  a customer's naming odd, weird, or unusual.
- Describe actions as "requesting revocations", never as revoking, removing,
  or deactivating access yourself, including in progress updates.
- Write email addresses as plain text, not links.
- State what you will NOT do and why (already offboarding, discovered apps
  excluded, no future-date scheduling) before stating what you will do.
- Be brief. One short confirmation question beats three long ones.
