# AccessOwl Skills

Manage access in plain English, from Slack or your terminal.

This repository contains **AccessOwl Skills**, the official AccessOwl skills
for AI assistants. They work in [Claude Tag](https://claude.com/docs/claude-tag/overview)
(Claude in Slack), [Claude Code](https://code.claude.com), and Codex, and
are built on the [AccessOwl REST API](https://docs.accessowl.com/api-reference/introduction).
Read-only questions are answered in one message. Every change is confirmed
once with you before anything is written. Requests follow your AccessOwl
approval policies, and the assistant never approves a request.

Ask things like:

> What does Maria have access to?
>
> Give Tom the same access as Lisa.
>
> Who has 1Password, grouped by role?

In Slack, mention the assistant, for example `@Claude what does Maria have
access to?`.

## The skills

| Skill | What you can say |
|---|---|
| `request-access` | "Request a HubSpot Marketing seat for Tom." |
| `grant-access` | "Mixpanel is set up for Dwight, mark the approved request granted." |
| `close-request` | "Deny Tom's pending Figma request, he no longer needs it." |
| `request-revocation` | "Tom no longer needs his HubSpot seat, revoke it." Or: "Jan was removed from Figma, mark the revocation as revoked." |
| `onboard-user` | "Onboard Sarah Lee, sarah@company.com, starting Monday, manager Mike Carter." |
| `offboard-user` | "Tom Smith is leaving, schedule the offboarding for Friday." |
| `list-access` | "What does Maria have access to?" |
| `mirror-access` | "Give Tom the same access as Lisa." |
| `access-report` | "Everyone in Marketing without HubSpot." |
| `import-userlist` | "Import this CSV into our Notion app." |
| `vendor-update` | "We finished the vendor review for Slack, record today's date." |
| `view-policies` | "Who approves Salesforce requests?" |
| `discovered-apps` | "Which apps has AccessOwl discovered?" |

## Install in Claude Tag

Before installing, [connect Claude Tag to AccessOwl](https://docs.accessowl.com/guides/ai/claude-in-slack): pair Claude with your Slack workspace and add your AccessOwl API token as a credential.

<!-- Install video goes here -->

Then, as a Claude organization admin:

1. **Fork this repository.** Fork `github.com/AccessOwl/claude-skills-for-customer` into a **private** repository in your organization's GitHub account. Claude only accepts private or internal repositories as organization plugin sources, so your fork is what Claude syncs from.
2. **Connect your fork.** In claude.ai, go to **Organization settings > Plugins**, add your fork via **Sync from GitHub** (installing the Claude GitHub App on it if prompted), and leave **Sync automatically** on.
3. **Attach the plugin.** Open the Access bundle that holds your AccessOwl credential, click **+** in its **Plugins** section, and add **AccessOwl Skills**.
4. **Add the recommended instructions.** Paste the [recommended instructions](#recommended-instructions) into the custom instructions for your workspace or your access channel.

That's it. Mention `@Claude` in your access channel and ask.

## Install in Claude Code

No fork needed. Run:

```text
/plugin marketplace add AccessOwl/claude-skills-for-customer
/plugin install claudetag-for-accessowl@accessowl-claude-skills
```

Then add the recommended instructions and set your credentials as described
below.

## Install in Codex

No fork needed. Run:

```bash
codex plugin marketplace add AccessOwl/claude-skills-for-customer
codex plugin add accessowl-skills@accessowl-skills
```

Then add the recommended instructions and set your credentials as described
below.

## Recommended instructions

Give every assistant the same instructions, so each one uses the skills and
waits for your yes before it changes anything, even when a request is phrased
as a direct command:

```text
For anything about AccessOwl access, applications, users, or policies, use the AccessOwl skills and follow them exactly, including their confirmation step: never create, change, close, or delete anything in AccessOwl until you have shown the skill's confirmation message and the person asking has answered yes to that message, even when the request is phrased as a direct command. Do not mention the skills or link their files in your replies.
```

- **Claude Tag:** paste it into the custom instructions for your workspace or
  your access channel.
- **Claude Code:** put it in an `AGENTS.md` file at the root of your project.
  Claude Code reads it automatically when the project has no `CLAUDE.md`. If
  the project has a `CLAUDE.md`, add the line `@AGENTS.md` to it. To use it in
  every project, put the text in `~/.claude/CLAUDE.md`
  ([Claude Code memory](https://code.claude.com/docs/en/memory)).
- **Codex:** put it in an `AGENTS.md` file at the root of your project. To use
  it in every project, put it in `~/.codex/AGENTS.md` (or
  `$CODEX_HOME/AGENTS.md`). Some Codex versions have not loaded the global
  file, so the project file is the most reliable
  ([Codex AGENTS.md](https://developers.openai.com/codex/guides/agents-md)).

## Credentials for terminal assistants

Claude Code and Codex read your AccessOwl API token from the environment.
Create an API token in AccessOwl under Settings, then API Tokens, and set it
in the shell you start the assistant from:

```bash
export ACCESSOWL_API_TOKEN="your-token"
# Optional, for a sandbox: a full URL ending in /api/v1
export ACCESSOWL_API_URL="https://sandbox.example.com/api/v1"
```

- `ACCESSOWL_API_URL` overrides any other configured AccessOwl host.
- Never paste a token into the chat. The assistant never asks for one and
  never accepts one pasted there.
- Any change (requests, grants, closing requests, imports, onboarding,
  offboarding, vendor updates) needs a token with write permission.

## Good to know

- Request skills create **requests**. An access request follows your
  approval policies, and the assistant reports its returned workflow status
  in plain words. It calls a request awaiting approval only while its status
  is `pending_approval`, never once it has been approved. A revocation
  request may begin removal immediately, depending on the application, so it
  is always confirmed first. The revocation skill can also mark a pending
  revocation revoked or rejected after you confirm.
- The grant skill records that a fully approved manual request was set up,
  then verifies the resulting access. The close skill denies or rejects only
  the open requests you confirm; it never grants them.
- The onboarding skill adds the new person you confirm, or onboards an
  existing person after a separate warning, and starts, schedules, or
  reschedules onboarding, which provisions what their access template
  matches. The offboarding skill offboards an Active person you confirm, now
  or on a date, which sends the offboarding notice and revokes the access
  AccessOwl tracks. Onboarding and offboarding cannot be undone through the API.
  Details of existing people are edited, and a planned offboarding is
  cancelled, on the person's profile in AccessOwl. People are never deleted.
- The user list import fully replaces an application's user list. It is the
  one deliberate full-replacement write: it is always previewed as Added,
  Changed, Removed, and Unchanged, and the list is re-read right before and
  after the write.
- The vendor skill makes only the direct metadata updates you confirm.
  Structure and policy changes are previewed, then completed in AccessOwl.
  The API gives no usable version check for an application's structure, so
  it cannot tell whether someone else changed it in the meantime, and a
  policy assignment is a complete-set replacement that could silently undo
  someone else's change, so the assistant refuses to write either one.
- Nothing is written to AccessOwl before you confirm it in the conversation,
  and every result is re-read before it is reported.
- Read-only questions (listings, reports) are answered directly, no
  confirmation needed.
- People are referred to by name. An email is added only when needed to
  distinguish two people with the same name, or in the confirmation of a
  change that cannot be undone.
- Statuses use the AccessOwl labels: Provisioning planned, Onboarding,
  Active, Inactive, Offboarding scheduled, Offboarding, and Offboarded.

## Staying up to date

- **Claude Tag:** Claude syncs from your fork, so pull upstream changes with
  GitHub's **Sync fork** button when a new version ships, or enable Actions
  on your fork once and the bundled `sync-upstream` workflow pulls them in
  daily. New conversations pick up skill updates automatically; ongoing ones
  keep the version they started with.
- **Claude Code:** run the commands below, then restart Claude Code.

  ```bash
  claude plugin marketplace update accessowl-claude-skills
  claude plugin update claudetag-for-accessowl@accessowl-claude-skills
  ```

- **Codex:** refresh the marketplace, then install the new version over the
  old one:

  ```bash
  codex plugin marketplace upgrade accessowl-skills
  codex plugin add accessowl-skills@accessowl-skills
  ```

## Learn more

- [AccessOwl Skills](https://docs.accessowl.com/guides/ai/accessowl-skills), the overview for every assistant
- [Connect Claude Tag to AccessOwl](https://docs.accessowl.com/guides/ai/claude-in-slack), the full Claude Tag setup guide
- [Manage access with Claude Tag](https://docs.accessowl.com/guides/ai/claude-workflows), conversation examples per use case
- [AccessOwl API reference](https://docs.accessowl.com/api-reference/introduction), everything the skills are built on

## Releasing

Updates are detected by version, so every release bumps `version` in
`.claude-plugin/marketplace.json`,
`plugins/accessowl/.claude-plugin/plugin.json`, and
`plugins/accessowl/.codex-plugin/plugin.json` together.
