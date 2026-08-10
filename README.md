# Gene of the Week

Sends one curated gene entry to Slack every Monday, pulled from `genes.yaml`.

## Setup

1. **Create a Slack Incoming Webhook.**
   In Slack: go to https://api.slack.com/apps -> "Create New App" ->
   "From scratch" -> pick your workspace -> under "Incoming Webhooks",
   activate it and add a webhook to the channel you want the messages
   posted to. Copy the resulting URL (looks like
   `https://hooks.slack.com/services/T000/B000/xxxx`).

2. **Push this folder to a GitHub repository** (public or private -
   private is fine, GitHub Actions works the same either way).

3. **Add the webhook URL as a repository secret.**
   In the repo: Settings -> Secrets and variables -> Actions ->
   "New repository secret" -> name it `SLACK_WEBHOOK_URL` -> paste the
   webhook URL as the value.

4. **Set your week-0 date.**
   Open `send_slack.py` and change `START_DATE` to the Monday you want
   your first entry to go out.

5. **Adjust the cron time for your timezone**, if 13:00 UTC (9am US
   Eastern) doesn't work for you. Edit the `cron:` line in
   `.github/workflows/weekly.yml`.

6. **Test it immediately** without waiting for Monday: go to the
   "Actions" tab on GitHub, select "Gene of the Week", click
   "Run workflow". Check Slack for the message.

## Weekly maintenance

Add new entries to the bottom of `genes.yaml`, commit, push. Nothing
else needs to change - the script always picks the entry for the
current week automatically. If you run out of entries, it loops back
to the top of the list rather than failing.

## Files

- `genes.yaml` - the content you curate.
- `send_slack.py` - picks this week's entry and posts it to Slack.
- `.github/workflows/weekly.yml` - the schedule that runs the script.
