# AccessOwl Skills for Claude

Manage access in plain English, right from Slack.

These skills connect [Claude](https://claude.com/docs/claude-tag/overview) to the [AccessOwl API](https://docs.accessowl.com/api-reference/introduction). Once set up, anyone on your team can ask things like:

- "Request Figma for jane@company.com"
- "What does Maria have access to?"
- "Give the new hire the same access as Lisa"
- "Who has 1Password, grouped by role?"
- "Here's our user export, get it ready for the AccessOwl import"

Claude answers and acts through your AccessOwl account. Every change is confirmed with you first, and every request still goes through your normal approval process. Claude never grants access itself.

## Setup

1. In AccessOwl, create an API token under **Settings → API Tokens**.
2. In Claude's admin settings for Slack, add the token as a Bearer credential and allow `api.accessowl.com`.
3. Register this repository as a plugin marketplace and install the AccessOwl plugin.

That's it. Mention @Claude in any channel and ask.

### Recommended: channel instructions

For the channel where your team manages access, add this to Claude's custom instructions to keep answers fast and consistent:

```
This channel is for managing access with AccessOwl. Always use the AccessOwl skills for anything about access, applications, users, or policies.

Rules for this channel:
- Answer read-only questions (who has access, reports, listings) immediately in one message. Never ask permission to look something up.
- No progress updates, checklists, or "on it" messages. The first reply is the answer or the confirmation question.
- Use short bullet points and tables. Plain language only: no IDs, no field names, no technical jargon, no em dashes.
- Before creating any request, confirm once in a single short message, then submit after a clear yes.
- Access requests and revocations always go through our normal approval process. Never say access was granted or removed, only that requests were submitted.
- Refer to people by name and email, and to applications and permissions by their exact AccessOwl names.
```

## The skills

| Skill | What you can ask |
|---|---|
| `request-access` | "Request a HubSpot Marketing seat for Tom." |
| `request-revocation` | "Tom no longer needs his HubSpot seat, revoke it." |
| `list-access` | "What does Maria have access to?" |
| `mirror-access` | "Give Tom the same access as Lisa." |
| `access-report` | "Everyone in Marketing without HubSpot." |
| `userlist-import-preflight` | "Validate this CSV against our Notion app before I import it." |
| `vendor-update` | "We finished the vendor review for Slack, record today's date." |
| `update-policy` | "Which policy covers Salesforce?" |

## Good to know

- Skills create **requests**. Approving them stays with your approvers, in your policies.
- Nothing is written to AccessOwl before you confirm it in the conversation.
- Read-only questions (listings, reports) are answered directly, no confirmation needed.
