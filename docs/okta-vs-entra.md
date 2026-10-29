# Okta vs Microsoft Entra ID: what I found building the same IAM system twice

I built the same project on both platforms: Okta (Integrator Free Plan) and Microsoft Entra ID (a free tenant, then a second tenant on a time-limited P2 trial). The organization model, the Python approach and the evidence were the same each time. This document records where the platforms actually differed in practice. It reflects two small lab builds, not a market comparison.

## Summary

| Area | Okta | Entra ID |
|---|---|---|
| Automation credential | Static API token sent as an `SSWS` header | App registration with a client secret, OAuth client-credentials flow through MSAL; each Graph permission granted and consented separately |
| New user | `POST /users?activate=true`, activation email | `POST /users` with a temporary password and a forced change at first sign-in; no activation email |
| Leaver | Deactivate endpoint; script verifies memberships afterwards | `accountEnabled=false`; script also revokes sessions and removes group memberships explicitly |
| Admin roles | Application Administrator and Help Desk Administrator assigned to the IT group, always active | The same two roles as PIM eligible assignments: MFA and a justification to activate, 1 hour maximum, an audit entry for each activation |
| MFA and policy | MFA on the admin account; MFA events visible in the System Log | Security defaults on the free tier (MFA registration forced at first sign-in); three scoped Conditional Access policies on the P2 trial |
| Access review | Scripted CSV report plus a policy | Native quarterly review with auto-apply, plus the scripted report |
| Log pull | System Log API (`/api/v1/logs`) | Graph sign-in logs (`/auditLogs/signIns`); policy names needed an extra permission |
| Detection test | 3 failed MFA attempts in 9 seconds, happened on its own | 3 failed passwords in 38 seconds, created deliberately |
| Free-tier ceiling | No expiry; the dashboard showed a 10 active-user cap | Identity basics are free; Conditional Access, PIM and access reviews need paid licensing |

## Differences that mattered

**Credentials.** Okta’s API token is one static value. Entra splits the same job into an app registration, a secret and individually consented permissions, and the app asks for a short-lived token. The first Entra connectivity test decoded the token to list its granted roles, which Okta never needed. I ended with two registrations on Entra, one for automation and one for the login app, so the sign-in app does not share a secret with an app that can write to users and groups.

**Leavers.** Okta’s deactivate call was enough, and the script checked memberships afterwards. In Entra, disabling an account does not remove its group memberships or end sessions that already exist, so the script revokes sessions and removes memberships itself. A leaver process that only flips the enabled flag looks finished and leaves access behind. I wrote the Entra behavior into the script as design reasoning and did not run an experiment to prove each part.

**Admin access.** Okta gave the IT group two scoped roles that stay active all the time. In Entra, PIM made the same two roles eligible: activation needs MFA and a written reason, expires after an hour, and appears in the audit log. The same least-privilege idea, with much less standing privilege.

**Policy order.** Conditional Access is evaluated after the first factor succeeds. The failed-password sign-ins in my logs show Conditional Access as not applied, while the successful sign-ins show the MFA policy applied and satisfied. A policy cannot stop password guessing; smart lockout and monitoring have to.

**SSO.** The FastAPI app needed only a different discovery URL to move from Okta OIDC to Entra OIDC. SAML took more effort on Entra: Okta had the RSA test service provider in its catalog, while Entra needed a non-gallery app and a metadata exchange in both directions.

## Where each build slowed me down

- **Okta:** I confused the admin console URL with the org base URL twice, in two different phases. Catalog apps like Slack need a domain I own, so I used bookmark apps.
- **Entra:** admin consent had to be granted for the Graph permissions; licenses need a usage location before they can be assigned; security defaults cannot run alongside Conditional Access; and the P2 trial could not be attached to a tenant created from a personal account, so I needed a second tenant. The trial also converts to a paid subscription if it is not cancelled, so I checked the billing page before relying on it.

## What I did not test

- Whether the Graph sign-in logs work on a free Entra tenant. I built the script on the P2 trial tenant.
- Okta Workflows, SCIM provisioning, and Okta’s governance and privileged-access products.
- Custom Okta admin roles scoped to resource sets, which I could not demonstrate on the free plan.
- Scheduled execution of the Entra scripts: a Windows scheduled task did not run, and the scheduling evidence comes from the Okta project.

## What I would say in an interview

The concepts are the same on both: joiner, mover and leaver automation, group-based access, least privilege, SSO over SAML and OIDC, access certification, and detection from sign-in logs. The differences were in the credential model, the defaults, what a disabled account still holds, and which features sit behind licensing. Building both showed me those differences directly instead of from documentation.
