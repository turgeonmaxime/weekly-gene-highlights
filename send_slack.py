"""
Gene-of-the-Week Slack sender.

What this script does, step by step:
1. Reads genes.yaml into a Python list of dicts.
2. Figures out which entry corresponds to "this week" by counting whole
   weeks elapsed since START_DATE, then taking that count modulo the
   list length. This means the schedule is fully determined by the
   calendar - it does not depend on remembering "where we left off",
   and it loops back to entry 0 once the list is exhausted.
3. Formats that entry into a Slack message using Block Kit (Slack's
   layout format for rich messages - plain text alone can't do
   headers/bold/dividers).
4. POSTs the message to a Slack Incoming Webhook URL, which is the
   simplest way to post into a channel without building a full Slack app.

Environment variables required:
- SLACK_WEBHOOK_URL: the webhook URL for the target Slack channel.

Optional:
- GENES_FILE: path to the YAML file (defaults to genes.yaml in the
  same directory as this script).
- START_DATE: ISO date (YYYY-MM-DD) for week 0. Defaults to a date
  hardcoded below - change it once, to whatever Monday you want week 1
  to land on.
"""

import os
import sys
import json
import datetime
import urllib.request
import urllib.error

import yaml  # PyYAML - not in the standard library, must be installed

# Change this to the Monday you want to count as "week 0" (the week
# your very first entry goes out). Every subsequent Monday advances
# the index by 1.
START_DATE = datetime.date(2026, 8, 10)


def load_genes(path):
    """Read the YAML file and return a list of dicts. Raises if the
    file is missing or malformed, rather than silently sending nothing -
    a failed run should be visible, not skipped quietly."""
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, list) or len(data) == 0:
        raise ValueError(f"{path} did not contain a non-empty list")
    return data


def pick_index(today, start_date, list_length):
    """Return which list index corresponds to 'today's week.

    (today - start_date).days gives elapsed days since week 0.
    Dividing by 7 and flooring gives elapsed whole weeks.
    Modulo list_length wraps back to the start once the list is
    exhausted, so the script never crashes just because you haven't
    added new entries yet - it just repeats the list.
    """
    elapsed_days = (today - start_date).days
    elapsed_weeks = elapsed_days // 7
    return elapsed_weeks % list_length


def build_slack_blocks(entry, week_number):
    """Build a Slack Block Kit payload. Block Kit is a list of
    'block' objects, each describing one visual chunk of the message
    (a header, a section of text, a divider, etc). Slack renders them
    top to bottom in the order given here."""
    text = (
        f"*Protein:* {entry['protein']}\n"
        f"*Pathway:* {entry['pathway']}\n"
        f"*Disease:* {entry['disease']}\n"
        f"*Mechanism:* {entry['mechanism']}\n"
        f"*Connection to prior weeks:* {entry['connection']}"
    )

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"Gene of the Week #{week_number}: {entry['gene']}",
            },
        },
        {"type": "section", "text": {"type": "mrkdwn", "text": text}},
    ]

    # "context" is a Block Kit block type meant for small supplementary
    # text - it renders in a lighter, smaller font below the main
    # content, which fits source links better than another full-size
    # section block would. get() rather than [] is used here so that
    # an entry missing a URL (e.g. one you added by hand and forgot to
    # fill in) doesn't crash the whole run - it just quietly loses that
    # one link.
    genecards_url = entry.get("genecards_url")
    medlineplus_url = entry.get("medlineplus_url")
    if genecards_url or medlineplus_url:
        # Slack mrkdwn link syntax is <url|display text>, not the
        # [text](url) syntax Markdown uses elsewhere.
        links = []
        if genecards_url:
            links.append(f"<{genecards_url}|GeneCards>")
        if medlineplus_url:
            links.append(f"<{medlineplus_url}|MedlinePlus>")
        blocks.append(
            {
                "type": "context",
                "elements": [{"type": "mrkdwn", "text": " · ".join(links)}],
            }
        )

    blocks.append({"type": "divider"})
    return {"blocks": blocks}


def post_to_slack(webhook_url, payload):
    """Send the payload as JSON to the webhook URL.

    Slack webhooks expect a POST request with a JSON body and
    Content-Type: application/json. urllib.request is the standard
    library's HTTP client - used here instead of the third-party
    'requests' library to keep dependencies minimal (only PyYAML is
    needed beyond the standard library)."""
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        webhook_url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req) as response:
            body = response.read().decode("utf-8")
            if body != "ok":
                # Slack's webhook endpoint returns the literal text "ok"
                # on success. Anything else indicates a problem even if
                # the HTTP status code was 200.
                raise RuntimeError(f"Unexpected Slack response body: {body}")
    except urllib.error.HTTPError as e:
        # HTTPError covers 4xx/5xx responses (e.g. invalid webhook URL,
        # channel deleted, malformed payload). Read the body for detail
        # before re-raising, since Slack usually explains the problem there.
        detail = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Slack webhook returned {e.code}: {detail}") from e


def main():
    webhook_url = os.environ.get("SLACK_WEBHOOK_URL")
    if not webhook_url:
        print("SLACK_WEBHOOK_URL is not set", file=sys.stderr)
        sys.exit(1)

    genes_path = os.environ.get(
        "GENES_FILE",
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "genes.yaml"),
    )

    start_date_str = os.environ.get("START_DATE")
    start_date = (
        datetime.date.fromisoformat(start_date_str) if start_date_str else START_DATE
    )

    genes = load_genes(genes_path)
    today = datetime.date.today()
    index = pick_index(today, start_date, len(genes))
    entry = genes[index]

    # week_number is 1-based and does NOT wrap - it's just for display,
    # so "Gene of the Week #53" still makes sense even though the list
    # has looped back to index 0.
    elapsed_weeks = (today - start_date).days // 7
    week_number = elapsed_weeks + 1

    payload = build_slack_blocks(entry, week_number)
    post_to_slack(webhook_url, payload)
    print(f"Sent week {week_number} (index {index}): {entry['gene']}")


if __name__ == "__main__":
    main()
