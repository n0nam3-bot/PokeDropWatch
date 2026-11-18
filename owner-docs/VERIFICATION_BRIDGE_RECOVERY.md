# Verification bridge recovery

This update fixes the duplicate alert chips and changes the Apps Script message bridge so each backend response is returned to the exact browser window that sent the request.

## Install the GitHub patch

1. Upload this ZIP to the repository `updates/` folder and commit it.
2. Open the **PokéDrop Watch** GitHub Actions workflow. Confirm that the patch is installed and the test step completes.
3. Refresh the public site after the workflow commits the changes. The alert chips should read **All activity**, **New items**, **First seen**, **Restocks**, **Price drops**, and **News**. The two first-seen/release-date chips must not share a label.

## Required: update the existing Apps Script deployment

GitHub Pages and Google Apps Script are separate deployments. Installing this ZIP does **not** replace the HTML already running on Google's servers.

1. Sign in to Google as `pokedropwatch.notify@gmail.com` and open the existing **PokéDrop Watch Backend** Apps Script project.
2. Open the HTML file named `Index` (not `Code.gs`). Replace its complete contents with the updated repository file `backend/apps-script/Index.html`.
3. Confirm the project still contains the current `Code.gs` functions `requestVerificationCode`, `verifyVerificationCode`, `adminLogin`, `adminListSubscribers`, `adminUpdateSubscriber`, `adminLogout`, `requestAdminPasswordReset`, and `completeAdminPasswordReset`.
4. If MailApp permissions have not already been granted, run `authorizeOwnerAccess` once from the Apps Script editor and approve the requested permissions.
5. Choose **Deploy → Manage deployments**. Edit the existing web app deployment, choose **New version**, and deploy. Keep the same deployment URL, execute as the notification mailbox owner, and allow access to anyone. Do not create a second deployment.
6. Reload `https://n0nam3-bot.github.io/PokeDropWatch/` and retry the email request.

If the site receives an Apps Script error, it will now display the backend's returned message instead of timing out silently. Check Apps Script **Executions** for the `requestVerificationCode` call. Also check the notification mailbox's Sent, Spam, and Promotions folders. A page-ready message alone does not prove that an email request ran or that an email was sent.

Do not repeatedly click the request button when it times out. A request can reach Apps Script even if its response is lost; wait at least one minute before trying again to avoid the email cooldown or duplicate requests.
