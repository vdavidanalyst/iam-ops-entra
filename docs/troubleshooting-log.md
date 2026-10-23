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