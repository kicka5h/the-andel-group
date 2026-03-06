#!/usr/bin/env python3
"""
send_newsletter.py — Send the monthly Andel newsletter to all active subscribers.

Usage:
    # Preview recipients without sending anything
    python3 scripts/send_newsletter.py --subject "March 2026 Update" --body scripts/newsletter_template.html --dry-run

    # Send for real
    python3 scripts/send_newsletter.py --subject "March 2026 Update" --body scripts/newsletter_template.html
"""

import argparse
import smtplib
import sys
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

# Allow importing app modules from the project root.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv()

from app.database import SessionLocal
from app.models import Subscriber

SENDER_NAME = "The Andel Group"
SENDER_EMAIL = "newsletter@andel.ca"
UNSUBSCRIBE_EMAIL = "unsubscribe@andel.ca"
SMTP_HOST = "localhost"
SMTP_PORT = 25


def fetch_subscribers(db):
    return (
        db.query(Subscriber)
        .filter(Subscriber.is_active == True)  # noqa: E712
        .order_by(Subscriber.subscribed_at)
        .all()
    )


def build_message(subscriber, subject, html_body):
    greeting = f"Hi {subscriber.first_name}," if subscriber.first_name else "Hello,"
    personalised = html_body.replace("{{greeting}}", greeting)

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = f"{SENDER_NAME} <{SENDER_EMAIL}>"
    msg["To"] = subscriber.email
    msg["List-Unsubscribe"] = f"<mailto:{UNSUBSCRIBE_EMAIL}?subject=unsubscribe>"
    msg["List-Unsubscribe-Post"] = "List-Unsubscribe=One-Click"
    msg.attach(MIMEText(personalised, "html"))
    return msg


def main():
    parser = argparse.ArgumentParser(description="Send the Andel Group newsletter")
    parser.add_argument("--subject", required=True, help="Email subject line")
    parser.add_argument("--body", required=True, help="Path to the HTML email file")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print recipients without sending any email",
    )
    args = parser.parse_args()

    html_body = Path(args.body).read_text(encoding="utf-8")

    db = SessionLocal()
    try:
        subscribers = fetch_subscribers(db)
    finally:
        db.close()

    total = len(subscribers)
    print(f"Active subscribers: {total}")

    if total == 0:
        print("No subscribers found. Exiting.")
        return

    if args.dry_run:
        print("\n[DRY RUN] — no email will be sent.\n")
        for s in subscribers:
            print(f"  {s.email}")
        print(f"\nTotal: {total}")
        return

    sent = 0
    failed = 0

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as smtp:
        for subscriber in subscribers:
            try:
                msg = build_message(subscriber, args.subject, html_body)
                smtp.sendmail(SENDER_EMAIL, subscriber.email, msg.as_string())
                print(f"  [OK]    {subscriber.email}")
                sent += 1
            except Exception as e:
                print(f"  [FAIL]  {subscriber.email} — {e}")
                failed += 1

    print(f"\nDone. Sent: {sent}  Failed: {failed}")


if __name__ == "__main__":
    main()
