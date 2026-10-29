# Troubleshooting Log (Entra ID)

### 1. Microsoft 365 Developer Program sandbox not available
**Symptom:** The plan assumed a free E5 sandbox tenant with Entra ID P2. 
**Cause:** The program now requires a qualifying subscription (e.g., Visual Studio Pro/Enterprise) and personal accounts generally don't qualify.
**Fix:** Used a free Entra ID tenant created through an Azure free account, and scheduled the 30-day P2 trial for the phases that need it.

### 2. "Interaction required" / AADSTS16000 in the Entra admin center
**Symptom:** Portal couldn't retrieve access tokens; the primary domain was just a tenant GUID.
**Cause:** A personal Microsoft account without a real tenant lands in a placeholder directory.
**Fix:** Created a proper directory via the Azure free account, which gave a .onmicrosoft.com domain and Entra ID Free.

### 3. Admin consent not granted on Graph permissions
**Symptom:** Permissions showed "Not granted for Default Directory".
**Cause:** Permissions were added but consent was never clicked.
**Fix:** Clicked "Grant admin consent"; connectivity test then showed all three roles in the token.

### 4. Web app refused to start: missing settings in .env
**Symptom:** RuntimeError: Missing Entra web app settings.
**Cause:** The sign-in app needs its own registration and secret; those variables didn't exist yet.
**Fix:** Created a separate IAM-Ops Entra Portal registration rather than reusing the automation app, so the login app doesn't share a secret with an app holding User/Group write permissions.

### 5. Outlook sign-in failed for the test user
**Symptom:** Signing in to Outlook on the web as the test user returned a 401 with CannotResolveExternalDirectoryOrganizationIdException.
**Cause:** The account was a valid identity but had no Exchange Online mailbox, because the tenant only held Entra ID licenses and no Microsoft 365 license. Authentication succeeded; entitlement to the mail service did not exist.
**Fix:** Tested accounts through myapps.microsoft.com, myaccount.microsoft.com and the demo app instead. Useful reminder that signing in and being entitled to a service are separate things.

### 6. P2 trial could not be attached to the personal-account tenant
**Symptom:** The P2 trial sign-up tried to create a new work account and tenant, and reported the existing domain as unavailable. The 365 admin center also refused a sign-in from the personal-account identity (login not supported for consumer users without business presence).
**Cause:** The first tenant was created from a personal Microsoft account, so it had no business presence for the billing and licensing flows.
**Fix:** Created a new tenant with the P2 trial for the paid-tier phases (Conditional Access, PIM, access reviews) and kept the free tenant as the record of Phases 0-4. Checked the subscription details page before relying on it, because the trial converts to a paid subscription if it is not cancelled before its end date.

### 7. Licenses need a usage location before assignment
**Finding:** A user cannot be assigned a license unless a usage location is set, and the provisioning script did not set one.
**Fix:** Added a usageLocation field to the user body in provision_user.py and set it on the admin account, before assigning P2 to the department groups.

### 8. Security defaults conflict with Conditional Access
**Symptom:** Custom Conditional Access policies cannot be enforced while security defaults are enabled.
**Cause:** The two are mutually exclusive; security defaults is the all-or-nothing baseline.
**Fix:** Confirmed the admin account had an MFA method registered, disabled security defaults, and created a replacement policy (CA03, MFA for all users) straight away. Created CA01 and CA02 in Report-only mode, with the admin account excluded, to avoid locking out the only administrator.

### 9. MFA registration page returned BadRequest
**Symptom:** During a test sign-in, the "Keep your account secure" page showed BadRequest and a timeout message.
**Cause:** Likely a session or browser state problem, since the message pointed at a timeout.
**Fix:** Retried in a clean private window with no other Microsoft sessions; the registration completed and the sign-in appeared in the logs.

### 10. PIM activation failed against the role's maximum duration
**Symptom:** Activating an eligible role as the test admin failed at first.
**Cause:** The role setting capped activation at 1 hour, and the requested duration exceeded it.
**Fix:** Lowered the requested duration to fit within the cap, and the activation succeeded and was recorded in the PIM audit log with its justification.

### 11. Conditional Access policy names missing from script output
**Symptom:** Sign-in log entries pulled through Graph showed a conditional access status but an empty policy list, while the portal showed the policies.
**Cause:** The applied policy list is only returned to apps holding a Conditional Access read permission; the automation app only had AuditLog.Read.All.
**Fix:** Added Policy.Read.ConditionalAccess (read-only) and re-ran the script, which then listed policy names per sign-in.

### 12. Windows scheduled task reported success but produced no output
**Symptom:** A scheduled task for the sign-in review returned result 0 and showed a last-run time, but no output or log file appeared. Two minimal test tasks (appending a line to a file) also produced nothing.
**Checked:** The wrapper script and the task definition were correct; the wrapper worked when run by hand. The task account matched the signed-in user and the Task Scheduler service was running.
**Outcome:** Cause not identified. The task was removed rather than left reporting success without running. No scheduled execution is claimed for the Entra scripts; the scheduling evidence comes from the Okta project (cron on a GCP VM). A result code of 0 is not proof that a task ran, so a scheduled job needs a log line of its own.