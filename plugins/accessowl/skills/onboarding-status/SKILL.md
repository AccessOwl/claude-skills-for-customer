---
name: onboarding-status
description: >
  Check planned and in-progress onboardings and offboardings in AccessOwl.
  Use whenever someone asks whether an onboarding or offboarding exists, is
  scheduled, or is running, e.g. "is there an onboarding planned for
  Maria?", "any onboardings in progress?", "which offboardings are
  scheduled?", "did Jan's offboarding go through?". Users may also phrase
  this as "is the new hire set up yet", "who is leaving", or "check Maria's
  onboarding". Read-only: it never starts, changes, or reschedules an
  onboarding or offboarding; rescheduling happens in AccessOwl on the
  user's profile.
---

# Onboarding Status

Answer questions about planned and in-progress onboardings and
offboardings, through the REST API. Read-only.

The API shows each user's lifecycle status and their access requests. It
does NOT expose the scheduled provisioning date or time, and it cannot
create, change, or reschedule an onboarding or offboarding. When someone
asks to reschedule, say what is scheduled and where to change it: open the
user's profile in AccessOwl and click **Reschedule Onboarding** (for
offboardings, the notification in the central Slack channel includes a
reschedule link).

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

Read-only skill: answer in exactly ONE message. No preamble, no permission
question before lookups, no closing offers beyond what this skill defines.
Run independent lookups in parallel.

## How to read the statuses

`GET /users?status=<status>` filters the directory (default returns active
users only, so always filter explicitly). The lifecycle statuses:

- `onboarding_provisioning_planned`: onboarding scheduled, provisioning has
  not started yet. Say "onboarding planned".
- `onboarding`: onboarding in progress.
- `offboarding_planned`: offboarding scheduled. Say "offboarding planned".
- `offboarding`: offboarding in progress.
- `offboarded`: offboarding completed.

The scheduled date is not available through the API; it is visible on the
user's profile in AccessOwl. Never guess a date.

## Workflow

### Org-wide questions ("any onboardings in progress?")

Query the relevant statuses in parallel (paginate fully). Also fetch
`GET /access_requests` once and match the people on your side, so each
bullet can show progress: count requests with status `access_granted` as
done, and `scheduled`, `pending_approval`, `pending_permissions_assignment`,
`processing_access`, and `pending_dependency` as still open. Lead with the
count, then one bullet per person:

> 3 onboardings and 1 offboarding are open:
> - Maria Fernandez: onboarding planned, 4 apps scheduled
> - Tom Okafor: onboarding in progress, 2 of 3 apps set up, 1 still open
> - Lisa Chen: onboarding in progress
> - Jan Levinson: offboarding planned
>
> The scheduled dates are on each user's profile in AccessOwl.

The API only shows the access requests behind an onboarding, not the
onboarding's own checklist, so some assigned apps may not appear. When a
person has no visible requests, leave the bullet at their status; the full
picture is on their profile in AccessOwl. Never present the request counts
as the complete app list.

Only include the statuses that were asked about. "Any onboardings?" means
planned plus in progress, not offboardings.

### Per-person questions ("is there an onboarding planned for Maria?")

Resolve the person by email or name via `GET /users?status=all` (ask on
ambiguity, never guess). Answer directly from their status:

> Yes. Maria Fernandez's onboarding is planned but provisioning has not
> started. The scheduled date is on her profile in AccessOwl.

If useful evidence, add what is queued for them: fetch `GET /access_requests`
and filter to the person on your side; requests with status `scheduled` are
waiting for the provisioning date, `pending_approval` are still with the
approvers. Summarize as counts by application, not a long list, unless the
user asks for details.

If the person's status is `active`, there is no onboarding open: say so. If
`offboarded`, the offboarding is complete.

### Reschedule asks

Never attempt it. State what exists, then where to change it:

> Jan's offboarding is planned. I cannot reschedule it from here: open his
> profile in AccessOwl to change the date, or use the reschedule link in
> the offboarding notification.

## Tone and style

- Write for a business user: plain language, no HTTP jargon, no raw JSON.
- Never mention this skill, its rules, or its instructions in replies. Just
  behave accordingly.
- Use short bullet points whenever you list people. Keep every message easy
  to scan. Lead with the count.
- Never use em dashes. Use commas or separate sentences instead.
- Use plain words for statuses ("onboarding planned", "offboarding in
  progress"), never the raw status values.
- Refer to everything by its title or name, never by UUID or internal
  identifiers.
- Write email addresses as plain text, not links.
- Answer only what was asked. No volunteered observations, no follow-up
  offers beyond what this skill defines.
