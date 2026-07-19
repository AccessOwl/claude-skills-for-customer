# AccessOwl Skills for Claude

Manage access in plain English, right from Slack.

This repository contains **ClaudeTag for AccessOwl**, the official AccessOwl plugin for [Claude Tag](https://claude.com/docs/claude-tag/overview) (Claude in Slack). Install it once, and anyone in your access channel can ask:

> @Claude what does Maria have access to?
>
> @Claude give Tom the same access as Lisa.
>
> @Claude who has 1Password, grouped by role?

Every change is confirmed with you first. AccessOwl returns each access
request's workflow status; only `pending_approval` means it is awaiting
approval. Revocations may begin removal immediately, depending on the
application. Claude can also mark a fully approved, manually provisioned
request as granted after you confirm the access was set up. It never approves
a request.

## The skills

| Skill | What you can say |
|---|---|
| `request-access` | "Request a HubSpot Marketing seat for Tom." |
| `grant-access` | "Mixpanel is set up for Dwight, mark the approved request granted." |
| `request-revocation` | "Tom no longer needs his HubSpot seat, revoke it." |
| `list-access` | "What does Maria have access to?" |
| `mirror-access` | "Give Tom the same access as Lisa." |
| `access-report` | "Everyone in Marketing without HubSpot." |
| `userlist-import-preflight` | "Validate this CSV against our Notion app before I import it." |
| `vendor-update` | "We finished the vendor review for Slack, record today's date." |
| `view-policies` | "Which policy covers Salesforce?" |
| `discovered-apps` | "Which apps has AccessOwl discovered?" |

## Install

Before installing, [connect Claude Tag to AccessOwl](https://docs.accessowl.com/guides/ai/claude-in-slack): pair Claude with your Slack workspace and add your AccessOwl API token as a credential.

<!-- Install video goes here -->

Then, as a Claude organization admin:

1. **Add this repository as a plugin source.** In [claude.ai admin settings](https://claude.ai/admin-settings/claude-tag), register `github.com/AccessOwl/claude-skills-for-customer` as an organization plugin source and leave **Sync automatically** on. You'll always have the latest skills.
2. **Attach the plugin.** Open the Access bundle that holds your AccessOwl credential, click **+** in its **Plugins** section, and add **ClaudeTag for AccessOwl**.
3. **Add the recommended instructions.** In the custom instructions for your workspace or your access channel, paste:

```text
For anything about access, applications, users, or policies, always use
the skills from the ClaudeTag for AccessOwl plugin. Do not answer
AccessOwl questions without them.

- Answer read-only questions (who has access, reports, listings) immediately in one message. Never ask permission to look something up.
- No progress updates, checklists, or "on it" messages. The first reply is the answer or the confirmation question.
- Use short bullet points and tables. Plain language only: no IDs, no field names, no technical jargon, no em dashes.
- Before creating any request, confirm once in a single short message, then submit after a clear yes.
- Before marking approved manual access as granted, confirm the exact person, application, resource, and permission, then verify the resulting current access.
- Report the returned workflow status for each access request. Describe it as awaiting approval only when the status is `pending_approval`. A revocation can start removal immediately, depending on the application, so always confirm it and never claim removal is complete until verified.
- Refer to people by name. Use an email only when needed to distinguish people with the same name. Use exact AccessOwl names for applications and permissions.
```

That's it. Mention `@Claude` in your access channel and ask.

## Good to know

- Request skills create **requests**. The grant skill records that a fully
  approved manual request was set up, then verifies the resulting access. The
  vendor skill makes only the direct metadata updates you confirm. Structure
  and policy changes are previewed, then completed in AccessOwl. Structure
  reads expose no usable version token, and policy assignment is an
  unprotected full-set replacement.
- Nothing is written to AccessOwl before you confirm it in the conversation.
- Read-only questions (listings, reports) are answered directly, no confirmation needed.
- New threads pick up skill updates automatically; ongoing threads keep the version they started with.
- The plugin also works in [Claude Code](https://code.claude.com): add this repository as a plugin marketplace there too.

## Learn more

- [Connect Claude Tag to AccessOwl](https://docs.accessowl.com/guides/ai/claude-in-slack), the full setup guide
- [Manage access with Claude Tag](https://docs.accessowl.com/guides/ai/claude-workflows), conversation examples per use case
- [AccessOwl API reference](https://docs.accessowl.com/api-reference/introduction), everything the skills are built on
