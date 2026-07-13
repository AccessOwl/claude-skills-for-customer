---
name: add-application
description: >
  Add applications to AccessOwl and define their roles and permissions. Use
  whenever someone wants to create one or more applications in AccessOwl or
  set up an application's access structure, e.g. "add Zoom to AccessOwl with
  Member, Admin, and Owner roles", "create these 10 apps from our vendor
  list", "here are the roles from our Notion admin console, set them up",
  "add an Editor role to our Figma app". Users may also phrase this as
  "onboard our apps", "seed our catalog", "import our app list", or paste a
  screenshot of an app's roles page. This skill creates and updates catalog
  entries after confirmation; it never connects an integration, imports
  users, or grants anyone access.
---

# Add Application

Create applications in AccessOwl and define their resources and permissions,
through the REST API. Works for one application or a whole list.

This skill only manages **catalog entries**. It never grants access, never
imports users, and never connects an integration. An application created here
is always a plain catalog entry: the API cannot create an integration-linked
application or pick one from AccessOwl's app directory, so do not claim the
new application is integrated, connected, or synced. To get users into an
application, point to access requests or the userlist import in AccessOwl
(open the application, click Edit, then Import).

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

State the split plainly in the confirmation ("3 new applications, Notion
already exists so I will only add the new roles to it").

### 2. Parse the roles and permissions

Accept any input: a plain list of app names, a spreadsheet, a pasted role
table, or a screenshot of an application's admin console.

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
- An application can also be created with no roles at all; it is then a bare
  catalog entry.

### 3. Resolve the owner

Creating an application requires an owner. Resolve the owner by email via
`GET /users`. If the user did not name an owner, ask once, for the whole
batch: "Who should own these applications? Share a name or email." Never
guess.

### 4. Confirm before writing

One short message covering everything, then one question. Show each new
application's structure as an indented list:

> Ready to create 2 applications in AccessOwl, owned by Maria Fernandez:
>
> **Zoom**
> - Role: Member, Admin, Owner
> - License: Basic, Licensed
>
> **Miro** (no roles provided, created without a structure)
>
> Notion already exists, so I will only add the Editor role to it.
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
> - Zoom: created with Role and License, 5 permissions
> - Miro: created
> - Notion: Editor role added
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
- State what you will NOT do and why (already exists, cannot set mandatory
  via the API) before stating what you will do.
- Be brief. One confirmation message for the whole batch beats one question
  per application.
