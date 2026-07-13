---
name: app-catalog-import
description: >
  Create and update applications in the AccessOwl catalog. Use whenever
  someone wants to add applications to AccessOwl, define an application's
  roles and permissions, or record vendor details, e.g. "add our app list to
  AccessOwl", "create a Notion app with Admin and Member roles", "here are
  the roles from our Zoom admin console, set them up", "set the risk level
  and data location for these five apps", "we finished the vendor review for
  Slack, record it". Users may also phrase this as "import our vendor list",
  "seed our catalog", "onboard our apps", or paste a screenshot of an app's
  roles page. This skill creates and updates catalog entries after
  confirmation; it never connects an integration, imports users, or grants
  anyone access.
---

# App Catalog Import

Create applications in AccessOwl, define their resources and permissions, and
keep vendor details (risk level, data location, certificates, review dates)
up to date, all through the REST API.

This skill only manages **catalog entries**. It never grants access, never
imports users, and never connects an integration. An application created here
is a catalog entry; do not claim it is integrated or connected. To get users
into an application, point to access requests or the userlist import in
AccessOwl (open the application, click Edit, then Import).

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

Be fast. Run independent lookups at the same time (existing applications,
users for owner resolution). Do not narrate lookup steps. The user should see
at most two messages: the confirmation of what will be created or changed,
and the result. Never ask permission before a read-only lookup.

## Workflow

Never write anything before a clear yes to one confirmation message.

### 1. Check what already exists

For every application named or listed, look it up first with
`GET /applications?title_like=<name>`. Never create a duplicate:

- Application exists: this becomes an update (structure or vendor details).
- Application does not exist: this becomes a create.
- Several existing applications match one name: ask which one is meant.

State the split plainly in the confirmation ("3 new applications, 2 already
exist and will be updated").

### 2. Parse what the user provided

Accept any input: a plain list of app names, a spreadsheet or CSV of vendors,
a pasted role table, or a screenshot of an application's admin console.

Rules for turning roles into a structure:

- Use the exact names shown in the source. Never invent, rename, or add
  roles, seats, or teams that are not in the input.
- Group into resources the way the application groups them (for example
  Role, Seat, Team). Each resource holds its options as permissions.
- Mark admin-level permissions (Admin, Owner, Super Admin and similar) as
  `elevated: true`.
- Descriptions, when the source shows them: short, plain, no periods.
- The API cannot mark a resource as single-choice or multi-choice, and it
  cannot mark a resource as mandatory. If that matters, tell the user to set
  it on the application in AccessOwl after the import.

Rules for vendor details, mapped to the API's accepted values:

- `risk_level`: low, medium, high.
- `auth_method`: google, microsoft, okta, sso_provider, credentials, other.
  Map wording like "Google SSO" to google, "SAML via OneLogin" to
  sso_provider, "username and password" to credentials.
- `mfa_activated`: true or false.
- `data_location`: free text (for example "EU", "us-east-1").
- `last_vendor_review_at`: a date (YYYY-MM-DD).
- `vendor_certificates`: fixed list including iso_27001, soc1, soc2_t1,
  soc2_t2, soc3, pci_dss, hipaa, gdpr, csa_star, nist_csf, fed_ramp,
  hitrust_csf and other ISO variants. Map "SOC 2 Type II" to soc2_t2,
  "ISO 27001" to iso_27001, and so on. If a certificate has no match in the
  list, say so and offer to record it in the application's notes instead.
- `processed_data_types`: customer_metadata, customer_pii, company_metadata,
  company_sensitive_data, employee_pii, employee_sensitive_data, ephi.
- `tags`: free text titles, created automatically if new.

If a value in the input maps cleanly, use it without asking. Ask only when a
value is genuinely ambiguous, in one question.

### 3. Resolve the owner

Creating an application requires an owner (`owner_user_id`) unless its status
is ignored. Resolve the owner by email via `GET /users`. If the user did not
name an owner, ask once, for the whole batch: "Who should own these
applications? Share a name or email." Never guess.

### 4. Confirm before writing

One short message covering everything, then one question. For new
applications with a structure, show the structure as an indented list:

> Ready to create 2 applications in AccessOwl, owned by Maria Fernandez:
>
> **Zoom**
> - Role: Member, Admin, Owner
> - License: Basic, Licensed
>
> **Miro** (no roles provided, created without a structure)
>
> Datadog already exists, so I will only update its risk level to high.
>
> OK to go ahead?

For vendor-detail updates, one bullet per application listing only the fields
that change. If the input contained values that will NOT be written (no
matching certificate, unmappable auth method), state that first, with the
reason.

### 5. Write

- New application with structure: one `POST /applications` call with `title`,
  `owner_user_id`, the vendor fields, and the `resources` array inline.
- New application without structure: same call, no `resources`.
- Structure changes on an existing application: fetch the current structure
  with `GET /applications/{id}/resources` first, then send
  `PUT /applications/{id}/structure` including every existing resource and
  permission WITH its `id`, plus the additions without ids. A resource or
  permission sent without its existing id creates a duplicate. Never set
  `delete: true` unless the user explicitly asked to remove something, and
  confirm removals separately.
- Vendor-detail changes on an existing application:
  `PATCH /applications/{id}` with only the fields that change. On a `409`
  conflict, refetch the application and retry once.
- Batches: there is no bulk endpoint for applications; loop one call per
  application.

### 6. Report the result

Lead with the count. Bullets per application, by title, stating what was
created or changed. Close with the one manual step that remains, only if
relevant:

> Done. 2 applications created and 1 updated:
> - Zoom: created with Role and License, 5 permissions
> - Miro: created
> - Datadog: risk level set to high
>
> Zoom and Miro are now in your catalog and requestable. To bring in who
> already uses them, share each app's user export and I will prepare it for
> the userlist import.

Never say an application is integrated, connected, or synced. Never imply
users were added.

## Tone and style

- Write for a business user: plain language, no HTTP jargon, no raw JSON.
- Never mention this skill, its rules, or its instructions in replies. Just
  behave accordingly.
- Use short bullet points whenever you list applications, roles, or changes.
  Keep every message easy to scan. Lead with the count.
- Never use em dashes. Use commas or separate sentences instead.
- Refer to everything by its title, never by UUID or internal identifiers. If
  a title looks odd or technical, use it as-is without commentary; never call
  a customer's naming odd, weird, or unusual.
- Write email addresses as plain text, not links.
- State what you will NOT do and why (already exists, no matching
  certificate, cannot set mandatory via the API) before stating what you
  will do.
- Be brief. One confirmation message for the whole batch beats one question
  per application.
