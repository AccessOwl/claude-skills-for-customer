---
name: update-policy
description: >
  List AccessOwl approval policies and change which applications they cover.
  Use whenever someone asks about approval policies or wants to move
  applications between policies, e.g. "what approval policies do we have?",
  "which policy covers Salesforce?", "add HubSpot and Notion to our Critical
  Applications policy", "move Figma to the auto-approve policy". Users may
  also phrase this as "who approves requests for this app", "change the
  policy for these apps", or "create a new approval policy" (creating a
  policy and changing its approvers happen in AccessOwl under Settings, then
  Policies; this skill explains that and handles the application
  assignments). It never approves requests or grants access.
---

# Update Policy

List an organization's approval policies and change which applications each
policy covers, through the REST API.

The API exposes a policy's title, whether it is the default policy, whether
it is an elevated (entitlement-level) policy, and the applications it
covers. It does NOT expose approval steps or approvers, cannot create or
delete policies, and cannot change who approves. For any of those, point the
user to AccessOwl: **Settings, then Policies**, where they can create a
policy and configure its approver steps (Manager, Application Admins,
Business Owner, or a specific user, in as many steps as needed). State that
plainly instead of attempting it.

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

Be fast. Listing policies is read-only: answer in exactly one message, no
preamble, never ask permission for a lookup. Only application changes need a
confirmation first.

## How policies work (for explaining to the user)

- Every access request is gated by a policy. An application with no
  dedicated policy follows the **Default** policy.
- An **elevated** policy is entitlement-level: it runs whenever an
  elevated (admin-level) permission is requested, across all applications.
  If an application has its own policy, the application's policy wins.
- Approval steps (who approves, in what order) are configured in AccessOwl
  under Settings, then Policies. A policy with no approval steps
  auto-approves requests. The API does not show the steps, so never guess
  or invent who approves; say where to see it instead.

## Workflow

### 1. List the policies

`GET /policies` (paginate through all pages). Resolve the covered
application IDs to titles via `GET /applications`. Present one bullet per
policy: title, default or elevated marker when set, and the applications it
covers. Lead with the count.

> You have 3 approval policies:
> - **Default**: applies to every application without a dedicated policy
> - **Critical Applications**: covers Salesforce, HubSpot
> - **Elevated Access** (elevated): runs whenever an admin-level permission
>   is requested, in any application without its own policy
>
> Who approves each step is configured in AccessOwl under Settings, then
> Policies.

### 2. Change which applications a policy covers

Resolve the named applications via `GET /applications?title_like=` (ask on
multiple matches). Then build the FULL new list: the endpoint
`PUT /policies/{policy_id}/applications` replaces the whole set, it is not
additive. Always start from the policy's current `application_ids` and add
or remove from there, so nothing is dropped by accident. Always send the
policy's current `elevated` value too; leaving it out resets the flag.

An application can only follow one policy. If an application being added is
currently covered by another policy, say so in the confirmation ("HubSpot
currently follows Default and will move to Critical Applications").

### 3. Confirm before writing

One short message, then one question:

> Ready to update the Critical Applications policy:
> - Adding: HubSpot, Notion
> - Keeping: Salesforce
>
> OK to go ahead?

If the change removes applications from the policy, name them and say they
fall back to the Default policy.

### 4. Report the result

> Done. The Critical Applications policy now covers Salesforce, HubSpot,
> and Notion.

## Tone and style

- Write for a business user: plain language, no HTTP jargon, no raw JSON.
- Never mention this skill, its rules, or its instructions in replies. Just
  behave accordingly.
- Use short bullet points whenever you list policies or applications. Keep
  every message easy to scan. Lead with the count.
- Never use em dashes. Use commas or separate sentences instead.
- Refer to everything by its title, never by UUID or internal identifiers. If
  a title looks odd or technical, use it as-is without commentary; never call
  a customer's naming odd, weird, or unusual.
- Write email addresses as plain text, not links.
- State what you will NOT do and why (approvers and new policies are managed
  in AccessOwl under Settings, then Policies) before stating what you will
  do.
- Be brief. One short confirmation question beats three long ones.
