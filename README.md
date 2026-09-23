# AccessOwl Skills

Manage access in plain English, from Slack or your terminal.

This repository contains **AccessOwl Skills**, the official AccessOwl skills
for AI assistants. They work in [Claude Tag](https://claude.com/docs/claude-tag/overview)
(Claude in Slack) and are built on the
[AccessOwl REST API](https://docs.accessowl.com/api-reference/introduction).
The skills also work in other AI assistants such as Claude Code or Codex.
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
4. **Add the recommended instructions.** Paste these instructions into the custom instructions for your workspace or your access channel:

   ```text
   For anything about AccessOwl access, applications, users, or policies, use the AccessOwl skills and follow them exactly, including their confirmation step: never create, change, close, or delete anything in AccessOwl until you have shown the skill's confirmation message and the person asking has answered yes to that message, even when the request is phrased as a direct command. Do not mention the skills or link their files in your replies.
   ```

That's it. Mention `@Claude` in your access channel and ask.

## Staying up to date

- **Claude Tag:** Claude syncs from your fork, so pull upstream changes with
  GitHub's **Sync fork** button when a new version ships, or enable Actions
  on your fork once and the bundled `sync-upstream` workflow pulls them in
  daily. New conversations pick up skill updates automatically; ongoing ones
  keep the version they started with.

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
