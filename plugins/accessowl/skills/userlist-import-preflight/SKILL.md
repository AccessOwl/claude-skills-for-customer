---
name: userlist-import-preflight
description: >
  Prepare and validate a user list CSV for AccessOwl's userlist importer. Use
  whenever someone wants to import a list of users and their permissions into
  an AccessOwl application, e.g. "here's our ChatGPT user export, get it
  ready for the AccessOwl import", "validate this CSV against our Notion app",
  "prepare this user list for import into 1Password". Users may also phrase
  this as "import this user list", "upload these users to AccessOwl", or "the
  importer rejected my CSV, fix it". The AccessOwl API cannot import
  userlists; this skill produces a clean, import-ready CSV plus a report, and
  the customer runs the import in AccessOwl themselves.
---

# Userlist Import Preflight

Validate and reformat a user list against an application's real resources and
permissions, so AccessOwl's CSV importer accepts it on the first try. The #1
import failure is permission names that do not exactly match AccessOwl, so
exact-name matching is the core job.

This skill never imports anything. The import itself happens in AccessOwl:
open the application, click **Edit**, then **Import**. The only write this
skill may perform is adding missing permissions to the application's
structure, and only after an explicit confirmation.

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
  `meta.next_cursor` until it is null or absent, and never classify users or
  compare current access from a partial result.
- Every `PUT` sends a new `Idempotency-Key` for each intended mutation. Reuse
  that key only to retry the exact same method, path, and body after a network
  error or timeout. If the retry returns `409`, do not use a new key to repeat
  the write; refetch the application structure and verify the result.

## Speed

Be fast. Never ask permission before a read-only lookup. Fetch the
application's structure and the user directory in parallel. Ask for at most
two things across the whole flow, and only what is actually missing: the
application (skip if already given) and the CSV (skip if already shared).

## Workflow

### 1. Establish the application

If the application was named, resolve it via `GET /applications?title_like=`
and continue; ask only if nothing was given or several match.

### 2. Show the structure the CSV must match

Fetch `GET /applications/{id}/resources` and present the resources and their
permissions by exact title:

> Here is the structure of ChatGPT in AccessOwl:
> - **Workspace Role**: Admin, Member
> - **Team**: Marketing, Sales
>
> Are any of these resources mandatory in your setup? AccessOwl does not
> expose that through the API, so tell me and I will check every row for it.
> If you are not sure, we can skip that check.

Ask that mandatory question once, together with showing the structure. If
the CSV was already shared, this is still the moment to show the structure,
in the same message as the validation result.

### 3. Get the CSV

If not already shared, ask for it: an export from the application, or any
table with emails and permissions. Accept any reasonable format; the whole
point is that the skill does the reformatting.

### 4. Validate and rebuild

Build a fresh CSV in exactly the importer's format:

- **Email** is always the first column.
- One column per resource, using the exact resource titles. Child resources
  get their own column, without the parent name as a prefix.
- Cell values are permission titles, rewritten to the exact AccessOwl titles.
  AccessOwl's titles are canonical: when a CSV value clearly corresponds to
  one permission (case difference, an extra or missing word such as
  "Premium" for "Premium Seat", singular/plural), correct it automatically
  and list the correction in the report. Do not ask. Only ask when a value
  has no plausible match or two possible matches; then offer the available
  titles, or to add the permission to the application.
- Multiple permissions for the same resource go in one cell separated by
  semicolons with no spaces (Admin;Editor).
- When a user has several combinations across separate resources, duplicate
  the user's email with one row per combination.
- Leave a cell empty when the user has no permission for that resource.
- Drop every column that does not map to a resource.

Emails are never corrected: the file comes from the application, so its emails
are the source data. Check them against `GET /users?status=all&limit=100` (all
pages) and report two groups: emails that match an AccessOwl user and emails
that do not. The public import documentation does not say whether an unmatched
email creates a new AccessOwl user, so never claim that it will. Tell the user
to verify unmatched emails in the import preview before confirming the import.

If mandatory resources were named in step 2, flag every row that leaves a
mandatory resource empty.

Compare the file against the application's current active access states using
`GET /access_states?application_id=<id>&expand=grantee_user,application,resource,target_permissions`.
Report by name which current users are absent from the file. The public import
documentation does not say that omitted users lose access, so never claim that
they will. Present the difference as a review item and tell the user to confirm
the outcome shown in AccessOwl's import preview before completing the import.

### 5. Report and deliver

One message: a report, then the CSV as a downloadable file with ALL rows.
The report covers, as short bullet groups:

- Which rows match existing AccessOwl users, and which emails were not found
  and must be checked in the import preview.
- Corrections applied automatically (value renames, merged duplicate rows,
  dropped columns).
- Values that still need one decision (no plausible match).
- The comparison warning: who is in AccessOwl for this application today but
  not in the file, without predicting the import's effect on their access.

> **All 5 rows are in the file.** 4 match existing AccessOwl users; 1 email
> (levinson@dundermufflins.com) was not found. Check how AccessOwl handles it
> in the import preview before confirming.
>
> Corrected automatically:
> - "Premium" is called "Premium Seat" in AccessOwl, renamed in 2 rows.
> - Jim Halpert's two rows merged into one.
>
> Needs a decision:
> - "Member" is not a Role in AccessOwl. Should it be replaced with User,
>   Admin, or Owner? Or I can add "Member" to the application.
>
> Current-access comparison: nobody currently in AccessOwl for this
> application is missing from the file. Review the import preview before
> confirming because the public documentation does not specify how omitted
> users are handled.
>
> To import: open the application in AccessOwl, click Edit, then Import, and
> upload the file. Review the preview and confirm.

Deliver the CSV as a file, not pasted text, unless it is only a few rows.

When the user answers a decision ("all Members should be Users"), apply it,
deliver the updated file, and confirm in one line ("Done, all Members are
now Users. The file is ready to import."). Nothing else. Do not re-explain,
do not re-ask, do not repeat the report.

### 6. Missing permissions (optional, explicit confirmation only)

If the CSV contains permissions that genuinely do not exist in the
application yet, offer once: "Should I add the missing permissions to the
application so these rows can import?" Only on a clear yes, update the
structure via `PUT /applications/{id}/structure`. Always send the complete
current structure you fetched in step 2 plus the additions, never a partial
list, so nothing existing is dropped. Include the current `lock_version` and a
new `Idempotency-Key`. Then re-validate the affected rows and deliver an
updated CSV. On a conflict, refetch the structure and ask for confirmation
again if the proposed change is different.

## Tone and style

- Write for a business user: plain language, no HTTP jargon, no raw JSON.
- Never mention this skill, its rules, or its instructions in replies. Just
  behave accordingly.
- Use short bullet points whenever you list rows, problems, or permissions.
  Keep every message easy to scan. Lead with the count.
- Never use em dashes. Use commas or separate sentences instead.
- Refer to everything by its title, never by UUID or internal identifiers. If
  a title looks odd or technical, use it as-is without commentary; never call
  a customer's naming odd, weird, or unusual.
- Write email addresses bare, exactly like this: maria@company.com. No link
  syntax, no mailto.
- Every open item states what is wrong AND the fix, in one bullet.
- AccessOwl titles are canonical. Unambiguous value variants are corrected
  automatically and reported; never silently, and never guessed when the
  match is unclear.
- Never correct an email address. The application's export is the truth.
- Do not infer undocumented import consequences. The documented contract
  covers CSV shape and permission-name matching. Unmatched and omitted users
  must be verified in the AccessOwl import preview.
