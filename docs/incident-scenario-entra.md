# Incident Scenario: Burst of Failed Sign-ins (Entra ID)

**Status:** controlled test. The failed sign-ins were created deliberately on a test account to exercise the detection rule and the response process. This is not a real incident.

## Detection

`scripts/pull_signin_logs.py` pulls sign-in events through Microsoft Graph and applies three rules. 
Rule 1 (3 or more failed sign-ins for one user within 10 minutes) flagged the test account `jordan.test`: three failures with error 50126 (invalid username or password) at 04:05:02, 04:05:28 and 04:05:40 UTC, a span of 38 seconds. Conditional Access was not evaluated on these events (status notApplied), because evaluation happens after the first factor succeeds. The failures were followed about seven minutes later by successful sign-ins with the correct password (04:12:45 UTC). Full timestamps are in `logs/signins.jsonl`.

Rules 2 (sign-ins blocked by Conditional Access) and 3 (successful sign-ins from different countries within an hour) found nothing, because a lab tenant does not produce those events. They are built and the logic is straightforward, but they were not exercised with real events.

## Why this pattern matters

- A burst of failures over seconds is faster than a person typing, which points toward password guessing or spraying.
- Failures followed by a success are more concerning than failures alone, because the success may mean a password was guessed.
- A user who simply mistyped a password usually produces one or two failures spread over a minute or more.

## Triage

1. Open the sign-in entries in the Entra admin center (Monitoring and health, Sign-in logs) for the user and time window.
2. Check the source IP address and country on each failure. The script does not store IP addresses, so this step happens in the portal. The same address across failures and the success suggests one actor.
3. Check whether the success came from the same address as the failures, and whether the account holder recognizes the location and device.
4. Look at the Conditional Access tab of each entry to see which policies were evaluated and whether MFA was required and completed. A success that was challenged for MFA and passed is far less concerning than one with no second factor.
5. Check whether other accounts show failures from the same address in the same period (spraying across users).
6. Contact the account holder through a different channel than the account itself, and ask whether the attempts were theirs.

## Response

**If the attempts were the user (benign):** no containment needed. Offer help with the password, note the event, and consider whether the user needs better sign-in guidance.

**If the attempts were not the user, or the user cannot be reached:**

1. Revoke the user's sessions (the deprovisioning script already uses the `revokeSignInSessions` call).
2. Reset the password and require a change at next sign-in.
3. Confirm the user still has only the MFA methods they registered themselves, and remove any they do not recognize.
4. If a success occurred from an unfamiliar address, review what the account accessed and any changes it made (audit logs).
5. If the account holds a sensitive group or an admin role, treat it as higher priority and escalate to the Security Lead.
6. Block the source address through a Conditional Access named location if the activity continues.

## Controls already in place

- **CA03** requires MFA for all users, so a guessed password alone does not complete a sign-in.
- **PIM** means admin roles are not standing privileges. An attacker who compromised an eligible admin would still have to activate the role with MFA and a justification, and that activation is logged.
- **Smart lockout** limits repeated guessing against one account.

## What I would add at scale

- Entra ID Protection sign-in risk and user risk policies, so risky sign-ins are challenged or blocked automatically.
- Alerting when the detection rules fire (email or chat) instead of a manual script run.
- Sending sign-in and audit logs to a central log store with longer retention than the portal keeps.
- Detection of password spraying across users, not only bursts against one account.

## Documentation

Each real incident would record the detection time, who investigated, the evidence reviewed, the decision, the containment taken, and the follow-up. For this test, the evidence is the script output, the portal sign-in entries, and the stored log file.
