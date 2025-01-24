# Simple and effective RSS Monitor that you can run from AWS Lambda or other serverless environment

import json
import feedparser
import requests

# List of RSS feeds to monitor
RSS_FEEDS = [
    "https://www.securityweek.com/rss.xml",
    "https://feeds.feedburner.com/TheHackersNews",
    "https://dailydarkweb.net/feed/"
]

# Keywords to monitor
KEYWORDS = ["Indonesia", "Data Breach", "Cyber Attack", "Ransomware", "Zero-Day"]

# Webhook URL for sending alerts
WEBHOOK_URL = "PUT YOUR WEBHOOK URL HERE"

def match_keywords(content):
    """
    Check if any of the keywords are present in the given content.
    """
    for keyword in KEYWORDS:
        if keyword.lower() in content.lower():
            return True
    return False

def send_alert(title, link, source):
    """
    Send an alert to the webhook URL.
    """
    message = {
        "text": f"🚨 **Threat Alert Detected**\n- **Title**: {title}\n- **Source**: {source}\n- **Link**: {link}"
    }
    headers = {"Content-Type": "application/json"}
    response = requests.post(WEBHOOK_URL, data=json.dumps(message), headers=headers)
    if response.status_code != 200:
        print(f"Failed to send alert: {response.text}")

def lambda_handler(event, context):
    """
    AWS Lambda entry point.
    """
    for feed_url in RSS_FEEDS:
        feed = feedparser.parse(feed_url)
        for entry in feed.entries:
            title = entry.get("title", "")
            description = entry.get("description", "")
            link = entry.get("link", "")
            
            # Combine title and description for keyword matching
            content = f"{title} {description}"
            
            if match_keywords(content):
                send_alert(title, link, feed_url)

    return {
        "statusCode": 200,
        "body": json.dumps("RSS Feed Monitoring Completed")
    }

