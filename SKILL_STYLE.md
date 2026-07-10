# Skill style guide

Every skill in this repo follows the pattern established by `request-access`
and `request-revocation`. Copy these rules into each new SKILL.md; skills are
self-contained, so the rules must live in the skill itself, not only here.

## Structure

Every SKILL.md has, in this order:

1. Frontmatter: `name` (kebab-case) and `description`. The description states
   what the skill does in request-only terms, gives example prompts, and adds
   a "Users may also phrase this as ..." sentence listing casual phrasings,
   always followed by a clarification that the skill never performs the
   underlying action itself.
2. A one-line statement of what the skill does, then what it never does
   (approve, grant, complete, provision).
3. **API basics**: base URL `https://api.accessowl.com/api/v1` plus the
   non-production host note, Bearer auth via the configured connection (never
   ask the user for a token), the 401/billing-redirect "API not enabled"
   stop, and 429 Retry-After handling.
4. **Speed**: run independent lookups in parallel, fetch only what's needed,
   no narration of lookup steps. Target: at most two messages, the
   confirmation question and the result.
5. **Workflow**: numbered steps. Resolve people by email (ask on ambiguity,
   never guess), resolve applications via `title_like` (ask on multiple
   matches), check existing/pending state before writing, confirm before any
   write, report with expectations.
6. **Tone and style** (copy verbatim, adjust nouns):
   - Write for a business user: plain language, no HTTP jargon, no raw JSON.
   - Use short bullet points whenever you list people, permissions, or
     requests. Keep every message easy to scan.
   - Never use em dashes. Use commas or separate sentences instead.
   - Refer to everything by its title, never by UUID or internal identifiers.
     If a title looks odd or technical, use it as-is without commentary;
     never call a customer's naming odd, weird, or unusual.
   - Describe actions as "submitting requests", never as provisioning,
     granting, revoking, or giving access yourself, including in progress
     updates.
   - Write email addresses as plain text, not links.
   - State what you will NOT do and why before stating what you will do.
   - Be brief. One short confirmation question beats three long ones. Do not
     narrate matching steps unless something needs the user's attention.

## Confirmation format

One short message, bullet list, one question:

> Ready to submit 17hats access requests:
> - Michael Scott: User
> - Jim Halpert: User
>
> OK to submit?

If only one option exists, state it as a fact, never as a choice or with
caveats. No write happens before a clear yes.

## Result format

Bullets for what was created, then expectations based on the application's
`provisioning_type`:

- `automatic`: "This application is integrated with AccessOwl", so AccessOwl
  processes it automatically after approval.
- `application_admin`: "This application is not integrated with AccessOwl",
  so an Application Admin is notified (there can be more than one).

## Hard rules

- Skills only request. Never call the grant endpoint. Never claim an access
  was granted, revoked, or completed.
- Mandatory resources are not exposed by the resources endpoint; they surface
  as a validation error on create. Translate that error into a clear question
  with the available options, never show the raw error.
- Bulk requests: max 10 items per call, one grantee per call.
