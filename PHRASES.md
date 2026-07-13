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

## Combos worth showing in the announcement

- Offboarding, end to end: "What does Jan have access to?" then "He left,
  revoke all of it."
- Onboarding in the HR channel: onboarding announcement lands, reply
  "@Claude give her the same access as Lisa."
- Review prep: "Who has Figma, grouped by role?" then "Revoke the two
  Editor seats that shouldn't be there."
