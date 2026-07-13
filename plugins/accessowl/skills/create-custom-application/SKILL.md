---
name: create-custom-application
description: >
  Create custom applications in AccessOwl for internal and self-hosted
  tools, and define their roles and permissions. Use whenever someone wants
  to add an internal application to AccessOwl or set up roles on a custom
  app, e.g. "add our internal admin dashboard to AccessOwl with User and
  Admin roles", "create an app for our data warehouse, IT owns it", "here
  are the roles of our billing tool, set them up", "add a Read-Only role to
  our admin dashboard". Users may also phrase this as "onboard our internal
  tools", "make our self-hosted GitLab requestable", or paste a role list
  or screenshot. This skill creates custom catalog entries after
  confirmation; the applications it creates can never be connected to an
  integration, and it never imports users or grants anyone access.
---

# Create Custom Application

Create custom applications in AccessOwl and define their resources and
permissions, through the REST API. Works for one application or a whole
list. This is for internal, self-hosted, and other tools AccessOwl will not
manage through an integration.

**Every application created here is a custom application.** It is not
matched to AccessOwl's built-in app catalog and it can never be connected
to an integration or an integration account; provisioning for it always
goes through its Application Admins. Make this clear before creating,
without asking about it: if the user wants the application connected to an
integration, tell them to add it in AccessOwl itself, where they can pick
the vendor from the built-in catalog and connect the integration. That is
not possible through the API today.

This skill never grants access and never imports users. To get users into
an application, point to access requests or the userlist import in
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
at most two messages: the confirmation of what will be created, and the
result. Never ask permission before a read-only lookup.

## Workflow

Never write anything before a clear yes to one confirmation message.

### 1. Check what already exists

For every application named, look it up first with
`GET /applications?title_like=<name>`. Never create a duplicate:

- Application does not exist: create it.
- Application exists and the user brought roles for it: update its structure
  instead of creating.
- Several existing applications match one name: ask which one is meant.

State the split plainly in the confirmation ("2 new applications, the
Billing Dashboard already exists so I will only add the new roles to it").

### 2. Parse the roles and permissions

Accept any input: a plain list of app names, a spreadsheet, a pasted role
table, or a screenshot of an application's admin console.

- Use the exact names shown in the source. Never invent, rename, or add
  roles, seats, or teams that are not in the input.
- Group into resources the way the application groups them (for example
  Role, Seat, Team). Each resource holds its options as permissions.
- Mark admin-level permissions (Admin, Owner, Super Admin and similar) as
  `elevated: true`. When the user calls a role high risk or admin-level,
  mark it elevated too.
- Descriptions, when the source shows them: short, plain, no periods.
- The API cannot mark a resource as single-choice or multi-choice, and it
  cannot mark a resource as mandatory. If that matters, tell the user to set
  it on the application in AccessOwl after the import.
- Every application in AccessOwl needs at least one resource with a
  permission; the API rejects a create without one. If no roles were
  provided, ask once, covering the whole batch: "AccessOwl needs at least
  one role per application. What are the roles for the Admin Dashboard? For
  example User and Admin, or share its role list." Never invent roles the
  user did not give you.

### 3. Resolve the owner

Creating an application requires an owner. Resolve the owner by email via
`GET /users`. If the user did not name an owner, ask once, for the whole
batch: "Who should own these applications? Share a name or email." Never
guess.

### 4. Confirm before writing

One short message covering everything, then one question. State the custom
nature once, then show each new application's structure as an indented
list:

> These will be created as custom applications, so AccessOwl will notify
> their Application Admins for provisioning instead of connecting an
> integration. Ready to create 2, owned by Maria Fernandez:
>
> **Admin Dashboard**
> - Role: User, Admin
>
> **Data Warehouse**
> - Role: Analyst, Engineer
>
> The Billing Dashboard already exists, so I will only add the Read-Only
> role to it.
>
> OK to go ahead?

### 5. Write

- New application: one `POST /applications` call with `title`,
  `owner_user_id`, and the `resources` array inline.
- Structure changes on an existing application: fetch the current structure
  with `GET /applications/{id}/resources` first, then send
  `PUT /applications/{id}/structure` including every existing resource and
  permission WITH its `id`, plus the additions without ids. A resource or
  permission sent without its existing id creates a duplicate. Never set
  `delete: true` unless the user explicitly asked to remove something, and
  confirm removals separately.
- Batches: there is no bulk endpoint for applications; loop one call per
  application.

### 6. Report the result

Lead with the count. Bullets per application, by title, stating what was
created or changed. Close with the one manual step that remains, only if
relevant:

> Done. 2 applications created and 1 updated:
> - Admin Dashboard: created with Role, 2 permissions
> - Data Warehouse: created with Role, 2 permissions
> - Billing Dashboard: Read-Only role added
>
> They are now in your catalog and requestable. To bring in who already uses
> them, share each app's user export and I will prepare it for the userlist
> import.

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
- State what you will NOT do and why (already exists, cannot connect an
  integration, cannot set mandatory via the API) before stating what you
  will do.
- Be brief. One confirmation message for the whole batch beats one question
  per application.
