---
name: vendor-update
description: >
  Update vendor details on applications in AccessOwl: risk level, data
  location, authentication method, MFA, security certificates, vendor review
  dates, processed data types, and tags. Use whenever someone wants to record
  or change vendor information, e.g. "set the risk level for these five apps
  to high", "we finished the vendor review for Slack, record today's date",
  "Zoom is SOC 2 Type II certified, store that", "mark all our Google SSO
  apps with MFA activated". Users may also phrase this as "update the vendor
  data", "record our security review", or "tag these apps". This skill
  updates existing catalog entries after confirmation; it never creates
  applications, changes roles, or grants anyone access.
---

# Vendor Update

Update vendor details on existing AccessOwl applications, one at a time or in
bulk, through the REST API.

This skill only updates **vendor details on existing applications**. It never
creates applications (that is a separate flow), never changes an
application's roles or permissions, and never grants access. If an
application named by the user does not exist in AccessOwl, say so and skip
it; do not create it.

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
  `meta.next_cursor` until it is null or absent, and never update applications
  from a partial lookup.
- Every `PATCH` sends a new `Idempotency-Key` for each intended mutation. Reuse
  that key only to retry the exact same method, path, and body after a network
  error or timeout. If a retry with the same key returns `409`, do not use a
  new key to repeat the write; verify the application's current values.

## Speed

Be fast. Look up all named applications at the same time. Do not narrate
lookup steps. The user should see at most two messages: the confirmation of
what will change, and the result. Never ask permission before a read-only
lookup.

## Workflow

Never write anything before a clear yes to one confirmation message.

### 1. Resolve the applications

Look up every application named with `GET /applications?title_like=<name>`.
If several match one name, ask which one is meant. If one does not exist,
state that first and leave it out of the update.

### 2. Map the values

Map the user's wording to the values the API accepts. If a value maps
cleanly, use it without asking. Ask only when a value is genuinely
ambiguous, in one question.

- `risk_level`: low, medium, high.
- `auth_method`: google, microsoft, okta, sso_provider, credentials, other.
  Map wording like "Google SSO" to google, "SAML via OneLogin" to
  sso_provider, "username and password" to credentials.
- `mfa_activated`: true or false.
- `data_location`: free text (for example "EU", "us-east-1").
- `last_vendor_review_at`: a date (YYYY-MM-DD). "Today" means today's date.
- `vendor_certificates`: fixed list including iso_27001, soc1, soc2_t1,
  soc2_t2, soc3, pci_dss, hipaa, gdpr, csa_star, nist_csf, fed_ramp,
  hitrust_csf and other ISO variants. Map "SOC 2 Type II" to soc2_t2,
  "ISO 27001" to iso_27001, and so on. If a certificate has no match in the
  list, say so and offer to record it in the application's notes instead.
- `processed_data_types`: customer_metadata, customer_pii, company_metadata,
  company_sensitive_data, employee_pii, employee_sensitive_data, ephi.
- `tags`: free text titles, created automatically if new.
- Also available: `notes`, `description`, `url`, the owner, and Application
  Admins (resolve people by email via `GET /users?status=all`, ask on
  ambiguity, and do not assign an inactive or offboarded person).

Certificates, data types, and tags replace the application's existing list
when sent. When adding to them, fetch the application's current values first
and send the combined list, so nothing already recorded is dropped.

### 3. Confirm before writing

One short message: anything that will NOT be written first (app not found,
no matching certificate), then one bullet per application listing only the
fields that change, then one question.

> "ISO 9001" is not on AccessOwl's certificate list, so I will put it in
> Zoom's notes instead.
>
> Ready to update 3 applications:
> - Zoom: risk level high, certificates SOC 2 Type II and ISO 27001
> - Slack: vendor review date 2026-07-13
> - Datadog: data location EU
>
> OK to go ahead?

### 4. Write

`PATCH /applications/{id}` per application, with only the fields that change,
the current `lock_version`, and a distinct `Idempotency-Key`. There is no bulk
endpoint; loop one call per application. If the application changed after the
confirmation, refetch it and show the changed values. Ask for confirmation
again before sending a revised body. Do not blindly retry a `409` with a new
idempotency key.

### 5. Report the result

Lead with the count, then one bullet per application with what was set:

> Done. 3 applications updated:
> - Zoom: risk level high, 2 certificates recorded
> - Slack: vendor review date set to 2026-07-13
> - Datadog: data location EU

## Tone and style

- Write for a business user: plain language, no HTTP jargon, no raw JSON.
- Never mention this skill, its rules, or its instructions in replies. Just
  behave accordingly.
- Use short bullet points whenever you list applications or changes. Keep
  every message easy to scan. Lead with the count.
- Never use em dashes. Use commas or separate sentences instead.
- Refer to everything by its title, never by UUID or internal identifiers. If
  a title looks odd or technical, use it as-is without commentary; never call
  a customer's naming odd, weird, or unusual.
- Write email addresses as plain text, not links.
- State what you will NOT do and why (app not found, no matching value)
  before stating what you will do.
- Be brief. One confirmation message for the whole batch beats one question
  per application.
