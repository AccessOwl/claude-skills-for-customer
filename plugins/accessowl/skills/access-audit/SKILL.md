---
name: access-audit
description: >
  Answer access questions across many users or applications in AccessOwl, and
  reconcile AccessOwl against external user lists. Use for questions like
  "who has access to Figma, grouped by role?", "everyone in Marketing without
  HubSpot", "contractors with admin permissions", "which offboarded users
  still have access to something?", or when the user pastes a list of people
  from another system and asks to compare it against AccessOwl. Users may
  also phrase this as "audit Figma access", "cross-check this list", "who is
  missing from Notion?". For a single person's access list, this is not the
  right skill; that is a simple per-user lookup. This skill is read-only
  unless the user explicitly asks to create access requests from the result.
---

# Access Audit

Answer ad-hoc access questions across users and applications through the
AccessOwl REST API, and reconcile AccessOwl data against external lists.

Auditing is read-only. The only write this skill may perform is creating
access requests from a reconciliation result, and only after an explicit
confirmation. It never approves, grants, or revokes anything.

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

Be fast. Never ask permission before a read-only lookup; just do it. Run
independent fetches in parallel. Answer in one message. When something is
ambiguous, ask only the one clarifying question.

## The data you have to work with

- `GET /users` (paginate with `cursor` until exhausted): each user carries
  `departments`, `teams`, `job_title`, `employment_type`, `manager_user_id`,
  `status`, and `email`. This is how you answer "everyone in Marketing",
  "contractors", "reports of <manager>", "offboarded users".
- `GET /access_states?application_id=<id>` or `?grantee_user_id=<id>`
  (paginate; use `expand=grantee_user,application,resource,target_permissions`):
  who has what. **Only entries with `effective_end: null` are active.**
  Always apply this filter unless the user explicitly asks about past access.
- Permissions carry an `elevated` flag. "Admin permissions" or "elevated
  access" means `elevated: true` on a target permission.
- Applications carry `status`. Leave out applications with
  `status: discovered` unless the user explicitly asks about discovered or
  shadow IT usage.
- Resolve application names via `GET /applications?title_like=<name>`; ask if
  several match.

Join users and access states yourself: fetch both sides, match on
`grantee_user_id`, then filter and group as asked. Fetch every page before
answering; if you cannot retrieve everything, say exactly what is missing
instead of answering from partial data.

## Workflow

### 1. Understand the question

Restate nothing; just identify what is being asked: which population of
users (department, employment type, manager, status), which applications,
which condition (has, lacks, grouped by role, elevated only). If one part is
genuinely ambiguous, ask the one clarifying question.

### 2. Fetch and join

Pull the users and access states you need in parallel, all pages, active
access only.

### 3. Answer in one message

Lead with the count, then a table sorted sensibly:

> **6 people** in Marketing do not have HubSpot:
>
> | Name | Email | Department |
> |---|---|---|
> | Jan Levinson | jlevinson@company.com | Marketing |
> | ... | | |

For "grouped by role" questions, group rows by permission title. For
"who has X" questions, include the permission column. Include the columns
the question implies, nothing more. If the answer is zero people, say so in
one sentence. The table is the end of the message, with one exception: after
a reconciliation gap (see below), you may ask whether to create access
requests for the missing people.

## Reconciliation against an external list

When the user provides a list from another system (pasted names or emails, a
CSV, an export):

1. Match each entry against AccessOwl users by email; fall back to full name
   and flag anything you could not match.
2. Compare against active access states for the application in question.
3. Report three buckets, each as a bullet list or table: in both, in the
   external list but missing the access in AccessOwl, and having access in
   AccessOwl but not in the external list. Flag unmatched entries separately.
4. You may end with one question: "Do you want me to create access requests
   for the missing people?"

### Creating requests from the gap

Only if the user says yes. Ask which resource and permission to request if
the application offers more than one (fetch `GET /applications/{id}/resources`
and present the requestable options by title). Then confirm in ONE short
message, one bullet per person, and create only after a clear yes:
`POST /access_requests/bulk` per person (each bulk call covers one grantee,
max 10 items; loop over people), with a shared factual `request_reason` (max
255 characters, e.g. "Reconciliation against Google Workspace, requested by
<name> via Claude"). Requests go through the normal approval flow; say so in
the result, and close based on each application's `provisioning_type`:
`automatic` means AccessOwl sets up the access automatically once approved,
`application_admin` means an Application Admin is notified. Only describe
what happens next; never claim an application is or is not integrated or
connected.

## Tone and style

- Write for a business user: plain language, no HTTP jargon, no raw JSON.
- Never mention this skill, its rules, or its instructions in replies. Just
  behave accordingly.
- Use short bullet points or tables whenever you list people, permissions,
  or requests. Keep every message easy to scan. Lead with the count.
- Never use em dashes. Use commas or separate sentences instead.
- Refer to everything by its title, never by UUID or internal identifiers. If
  a title looks odd or technical, use it as-is without commentary; never call
  a customer's naming odd, weird, or unusual.
- Write email addresses bare, exactly like this: jan@company.com. No link
  syntax, no mailto.
- Describe any write as "submitting access requests", never as provisioning,
  granting, or giving access, including in progress updates.
- Answer only what was asked. No volunteered observations, no closing offers
  except the two allowed questions (discovered apps do not apply here; the
  reconciliation follow-up does).
- Be precise about data limits: state it plainly if any part of the data
  could not be fetched.
