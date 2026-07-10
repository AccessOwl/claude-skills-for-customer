---
name: request-access
description: >
  Create AccessOwl access requests for a user. Use whenever someone asks to
  request access to an application for themselves or a colleague, or says a
  person needs an application, e.g. "request Figma for jane@company.com",
  "Maria needs HubSpot with a Marketing seat", "Tom needs access to Notion".
---

# Request Access

Create access requests in AccessOwl through its REST API.

This skill only **requests** access. It never approves, grants, or provisions
anything itself. Every request goes through the organization's normal approval
process: approvers are notified as usual and the full audit trail is kept.
Never call the grant endpoint.

## API basics

- Base URL: `https://api.accessowl.com/api/v1`
- Authentication: the AccessOwl API token configured for this environment
  (Bearer token). Do not ask the user for a token.
- If a request returns `401` or redirects to a billing page, the AccessOwl API
  is not enabled for this organization. Tell the user to contact AccessOwl
  support to enable it, and stop.
- On `429`, wait the number of seconds in the `Retry-After` header, then retry.

## Workflow

Follow these steps in order. Never skip the confirmation step.

### 1. Identify who the access is for

You need the grantee's AccessOwl user ID. List users via `GET /users` and
match on email address. If you were given a name and more than one person
matches, ask which one is meant. Never guess between similar names or invent
an email address.

### 2. Identify the application

Find the application with `GET /applications?title_like=<name>`. If several
applications match, list their titles and ask which one is meant.

### 3. Look up what can be requested

Fetch the application's structure with `GET /applications/{id}/resources`.
Present the requestable resources and their permissions to the user in plain
language, using the exact titles from AccessOwl. For example:

> Here is what can be requested for HubSpot:
> - **Seat**: Core, Enterprise, View-Only
> - **Permission Set**: Marketing, Sales, Service
>
> Which should I request for Maria?

Only include resources and permissions where `requestable` is `true`. If a
resource has `multiple_permissions_selectable: false`, only one of its
permissions can be picked. Mention when a permission is marked `elevated`
(admin-level), since approvers scrutinize those.

If the user already told you exactly what to request, you can skip the
question, but still fetch the structure so you use real permission IDs.

### 4. Check what the person already has

Before creating anything, check `GET /access_states?grantee_user_id=<id>&application_id=<id>`
and the pending requests from `GET /access_requests` (filter by grantee and
application in your own comparison).

If part of what was asked for already exists or is already pending, do not
request it again. Say so clearly and professionally, for example:

> Maria already has the Enterprise seat, so I won't request that again.
> I'll create a request for the Marketing permission set only.

### 5. Confirm before creating

Summarize exactly what you are about to do: the person, the application, the
resources and permissions by title, and the request reason. Ask for a clear
go-ahead. Do not create requests before receiving it.

### 6. Create the requests

- Single request: `POST /access_requests` with `user_id`, `resource_id`,
  `permission_ids`, and `request_reason`.
- Several at once (same person): `POST /access_requests/bulk` with a shared
  `request_reason` and up to 10 items per call; loop for more. Each bulk call
  covers one grantee only.
- `user_id` is required: it is the person receiving the access.
- `request_reason` is required, max 255 characters. Use the reason the user
  gave, or a short factual one such as "Requested by <name> via Claude".

### 7. Handle mandatory resources

Some organizations mark certain resources as mandatory: other permissions in
that application cannot be granted unless the person already has the mandatory
resource or it is part of the request. The API does not label which resources
are mandatory upfront; instead, creating a request without them returns a
validation error listing the required permissions.

When that happens, do not show the raw error. Explain it and ask:

> AccessOwl requires a **Seat** for HubSpot before other permissions can be
> requested, and Maria doesn't have one yet. Which seat should I include:
> Core, Enterprise, or View-Only?

Then create the request again with the mandatory resource included. If the
person already holds the mandatory resource, no extra step is needed.

### 8. Report the result

Confirm what was created, by title, and make clear that approval is a separate
step that has not happened yet. Then tell the user what happens after
approval, based on the application's `provisioning_type` (from the
application object):

- `automatic`: the application is integrated with AccessOwl, so once a request
  is approved, AccessOwl provisions the access automatically.
- `application_admin`: the application is not integrated with AccessOwl, so
  once a request is approved, an Application Admin is notified to set up the
  access in the application (there can be more than one admin).

> Done. I created 2 access requests for Maria: HubSpot Enterprise seat and
> Marketing permission set. They now go through your normal approval flow.
> HubSpot is integrated with AccessOwl, so once approved, the access will be
> provisioned automatically.

If a request depends on a mandatory resource that was requested at the same
time, mention that it will show as "Pending dependency" until the mandatory
resource is provisioned.

## Tone and style

- Write for a business user: plain language, no HTTP jargon, no raw JSON.
- Refer to everything by its title, never by UUID.
- Always state what you will NOT do and why (already granted, already pending,
  not requestable), before stating what you will do.
- Be brief. One short confirmation question beats three long ones.
