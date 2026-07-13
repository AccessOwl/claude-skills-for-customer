# Customer phrase library

Real phrases customers can say to Claude for each skill, grouped by why
they'd care. Source of truth for the docs recipes page, the product
announcement, and the trigger examples in each skill's description.

Honest limits to keep out of marketing claims:

- The API knows who **holds** access, not who **uses** it. No last-activity
  data, no usage questions.
- "Since when" works (access states carry a start date). "How was it
  discovered" (OAuth, SAML, email) does not exist in the API.
- Skills only request. Approval always stays with the customer's normal flow.

## request-access

**Onboarding**

- "Maria starts Monday in Marketing. Request Slack, Notion, and HubSpot for
  maria@company.com."
- "Set up the new hire with Figma and 1Password."
- "Request a HubSpot Marketing seat for Tom."

**Day-to-day requests**

- "Request Figma for jane@company.com."
- "Tom needs access to Notion."
- "I need access to Tableau for the quarterly report."

**Role changes**

- "Jan moved to Sales. He needs Salesforce with the Sales permission set."
- "Maria is taking over billing, request the Finance role in NetSuite for
  her."

**Exploring what's requestable**

- "What roles can be requested for HubSpot?"
- "Which permissions does our Zoom app offer?"

## request-revocation

**Offboarding**

- "Jan left, his Salesforce access should be removed."
- "Request revocation of everything Jan has in HubSpot."
- "Maria's last day is Friday, remove her Figma access."

**Least privilege cleanup**

- "tom@company.com no longer needs his HubSpot seat."
- "The contractor project ended, take away Maria's Slack access."

**Follow-up on findings**

- "The review flagged Jan's Figma access, revoke it."
- "Remove the admin role we gave Tom for the migration."

## list-access

**Quick lookups**

- "What does Maria have access to?"
- "Show me Tom's apps."
- "Does Jan have Figma?"

**People management**

- "List the applications for jan@company.com before our 1:1."
- "What can the new intern use right now?"

**Shadow IT**

- "What apps has AccessOwl discovered for Mike?"
- (after any listing) "Yes, show me the discovered apps."

## mirror-access

**Onboarding by example**

- "Give the new hire the same access as Lisa."
- "Tom should have everything Maria has."
- "Onboard Jan like a typical support agent, copy what Sam has."

**Catching up a teammate**

- "For every access Lisa has that Tom doesn't, create a request."
- "Make Tom match Maria's HubSpot setup."
- "Copy Jan's apps to Tom, but only some of them, I'll pick."

## access-report

**Security hygiene**

- "Which offboarded users still have active access to something?"
- "Who has admin permissions in Google Workspace?"
- "Show me everyone with elevated access in more than one app."
- "List external contractors with access to our customer data tools."

**Before an Access Review**

- "Who has Figma, grouped by role?"
- "Who got access to Salesforce in the last 30 days?"
- "Which of Jan's direct reports have HubSpot?"

**Coverage gaps**

- "Everyone in Marketing without HubSpot."
- "Which new joiners this month are still missing Slack?"
- "Does everyone in Support have both Zendesk and Notion?"

**Spend questions**

- "How many people have a Zoom license, by role?"
- "Who has both Salesforce and HubSpot?"
- "Which apps does the Sales team hold access to?"

**Reconciliation**

- "Here's our Google Workspace user list, who's missing from Outline in
  AccessOwl?"
- "Compare this CSV from our HR system against who has BambooHR access."

## userlist-import-preflight

**Getting a user list in**

- "Here's our ChatGPT user export, get it ready for the AccessOwl import."
- "Validate this CSV against our Notion app before I import it."
- "Prepare this user list for import into 1Password."

**Fixing import errors**

- "The importer says my permission names don't match, fix this CSV."
- "Which rows in this file won't import, and why?"

**Structure first**

- "What structure does our HubSpot app expect for a user list import?"
- "Add the missing permissions to the app so this list can import."

## create-custom-application

**Adding internal tools**

- "Add our internal admin dashboard to AccessOwl with User and Admin roles."
- "Create an app for our data warehouse, IT owns it."
- "Make our self-hosted GitLab requestable in AccessOwl."
- "Add these three internal tools to AccessOwl, here's the list."

**Defining roles and permissions**

- (pasted role list or screenshot) "Here are the roles of our billing tool, set them up."
- "Add a Read-Only role to our admin dashboard."
- "Our internal CRM got a new Support role, add it."

## vendor-update

**Risk and compliance bookkeeping**

- "Set the risk level for these five apps to high."
- "We finished the vendor review for Slack, record today's date."
- "Zoom is SOC 2 Type II and ISO 27001 certified, store that."
- "Mark all our Google SSO apps with MFA activated."

**Housekeeping**

- "Tag all our marketing tools with Marketing."
- "Datadog stores data in the EU, record that."
- "Maria took over as owner of Figma, update it."

## update-policy

**Understanding the setup**

- "What approval policies do we have?"
- "Which policy covers Salesforce?"
- "Which apps auto-approve requests?"

**Moving apps between policies**

- "Add HubSpot and Notion to our Critical Applications policy."
- "Move Figma to the auto-approve policy."
- "Every finance tool should follow the Finance policy."

## onboarding-status

**Keeping an eye on the pipeline**

- "Any onboardings in progress?"
- "Which offboardings are scheduled?"
- "Who is currently being onboarded?"

**Checking one person**

- "Is there an onboarding planned for Maria?"
- "Is the new hire set up yet?"
- "Did Jan's offboarding go through?"

## Combos worth showing in the announcement

- Offboarding, end to end: "What does Jan have access to?" then "He left,
  revoke all of it."
- Onboarding in the HR channel: onboarding announcement lands, reply
  "@Claude give her the same access as Lisa."
- Review prep: "Who has Figma, grouped by role?" then "Revoke the two
  Editor seats that shouldn't be there."
