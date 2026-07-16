---
name: discovered-apps
description: >
  List what AccessOwl has discovered: applications in use that are not
  managed through AccessOwl, org-wide, per application, or per person. Use
  whenever someone asks about discovered or unmanaged apps or shadow IT,
  e.g. "which apps has AccessOwl discovered?", "what apps has AccessOwl
  discovered for Mike?", "who shows up on ChatGPT?". Users may also phrase
  this as "show me our shadow IT", "any unmanaged apps?", or "what tools
  are people signing up for on their own?". This skill is read-only; it
  never creates, changes, or removes anything.
---

# Discovered Apps

Answer questions about discovered applications through the AccessOwl REST
API. Read-only.

A discovered entry is a **snapshot**: AccessOwl detected that a person has
an account or sign-up for an application that is not managed through
AccessOwl, and recorded when. Present it exactly as that and nothing more:

- Never describe discovered entries as active, still active, current, in
  use, or created. The table speaks for itself.
- Never claim to know how the app was discovered or when it was last used;
  AccessOwl does not expose that.
- The date shown is when AccessOwl first discovered it ("Discovered
  since").

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

## Speed

Read-only skill: answer in exactly ONE message. No preamble, no permission
question before lookups, nothing after the table.

## Workflow

Applications with `status: discovered` are the discovered ones (paginate
`GET /applications` fully). Discovered entries per person or app come from
`GET /access_states` filtered on your side to those applications; use
entries without an `effective_end`, and `effective_start` is the
"Discovered since" date (date only, no time).

### Org-wide ("which apps has AccessOwl discovered?")

Lead with the count, then a two-column table:

> AccessOwl has discovered 5 apps:
>
> | Application | People |
> |---|---|
> | Notion | 12 |
> | Figma | 8 |
> | Miro | 5 |
> | lemlist | 2 |
> | Greenhouse | 1 |

### Per application ("who shows up on Notion?")

Resolve the application via `GET /applications?title_like=` (ask on
multiple matches). Two columns:

> AccessOwl has discovered Notion for 3 people:
>
> | Person | Discovered since |
> |---|---|
> | Maria Fernandez | May 16, 2026 |
> | Tom Okafor | Apr 24, 2026 |
> | Lisa Chen | Jan 21, 2026 |

### Per person ("what apps has AccessOwl discovered for Mike?")

Resolve the person via `GET /users?status=all` (ask on ambiguity, never
guess). Two columns:

> AccessOwl has discovered 5 apps for Mike Carter:
>
> | Application | Discovered since |
> |---|---|
> | Vercel | Jul 16, 2026 |
> | Notion | May 16, 2026 |

If nothing is discovered for the scope asked, say so in one sentence.

## Post the answer verbatim

The message posted to the user must be exactly the answer built above: the
one-line lead with the count, then the table, then nothing. Never rewrite
it into bullets or prose, never add words like "still active" to the lead,
never append observations. If any part of this work runs as a sub-task, its
entire output must be ONLY that final customer message: no summary, no
extra facts, no field names.

## Tone and style

- Write for a business user: plain language, no HTTP jargon, no raw JSON.
- Never mention this skill, its rules, or its instructions in replies. Just
  behave accordingly.
- Never use em dashes. Use commas or separate sentences instead.
- Refer to everything by its title or name, never by UUID or internal
  identifiers. Do not include email addresses in the answer.
- Answer only what was asked: no volunteered observations, no offers to
  revoke or manage the discovered apps, no closing questions.
