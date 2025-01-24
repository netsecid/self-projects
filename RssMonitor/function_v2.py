import json
import re
import feedparser
import requests
from concurrent.futures import ThreadPoolExecutor

# ------------------------------
# Lambda Function: RSS Feed Monitor
# ------------------------------
# Description:
# This AWS Lambda function monitors multiple RSS feeds for specific keywords 
# and sends an alert via a webhook when a match is found.
#
# Features:
# - Fetches RSS feed URLs and keywords from an S3 bucket.
# - Matches keywords using regex for powerful and flexible matching.
# - Processes feeds concurrently to improve speed and reduce AWS costs.
# - Sends detailed alerts with matched keywords and source information.
# - Provides informative logs (feeds checked, matches found, alerts sent).
#
# How to Use:
# 1. Store your RSS feed URLs and keywords in an S3 bucket (JSON file).
# 2. Deploy this function in AWS Lambda.
# 3. Configure the required environment variables (S3_BUCKET, S3_KEY, WEBHOOK_URL).
# 4. Use EventBridge to schedule the Lambda function (e.g., every 5 minutes).

# ------------------------------
# Environment Variables
# ------------------------------
# Set the following in your AWS Lambda environment:
# - S3_BUCKET: Name of the S3 bucket where the JSON file is stored.
# - S3_KEY: Key (path) to the JSON file in the S3 bucket.
# - WEBHOOK_URL: Webhook URL for sending alerts (e.g., Slack or Teams).

import boto3

# Initialize the S3 client
s3_client = boto3.client("s3")

# Environment variables (set these in the AWS Lambda console)
S3_BUCKET = "rss-monitoring-data"  # Replace with your bucket name
S3_KEY = "rss_feeds_and_keywords.json"  # Replace with your file path
WEBHOOK_URL = "https://hooks.slack.com/services/your/webhook/url"  # Replace with your webhook URL


def load_config_from_s3(bucket, key):
    """
    Load RSS feeds and keywords from a JSON file in an S3 bucket.
    """
    try:
        response = s3_client.get_object(Bucket=bucket, Key=key)
        config = json.loads(response['Body'].read().decode('utf-8'))
        return config
    except Exception as e:
        raise Exception(f"Error loading configuration from S3: {e}")


def match_keywords(content, keywords):
    """
    Use regex to match keywords in the content.
    """
    matches = []
    for keyword in keywords:
        if re.search(rf"\b{keyword}\b", content, re.IGNORECASE):
            matches.append(keyword)
    return matches


def process_feed(feed_url, keywords):
    """
    Parse and process an RSS feed to check for keyword matches.
    """
    results = {"feed": feed_url, "matches": []}
    try:
        feed = feedparser.parse(feed_url)
        for entry in feed.entries:
            title = entry.get("title", "")
            summary = entry.get("summary", "")
            content = f"{title} {summary}"  # Combine title and summary for matching

            matched_keywords = match_keywords(content, keywords)
            if matched_keywords:
                results["matches"].append({
                    "title": title,
                    "url": entry.get("link", ""),
                    "keywords": matched_keywords
                })
    except Exception as e:
        results["error"] = str(e)

    return results


def send_alert(alerts):
    """
    Send an alert via webhook if any matches are found.
    """
    message = {
        "text": "🚨 **Threat Intelligence Alert** 🚨\n",
        "attachments": []
    }

    for alert in alerts:
        for match in alert["matches"]:
            attachment = {
                "title": match["title"],
                "title_link": match["url"],
                "text": f"**Matched Keywords**: {', '.join(match['keywords'])}\n**Source**: {alert['feed']}"
            }
            message["attachments"].append(attachment)

    headers = {"Content-Type": "application/json"}
    response = requests.post(WEBHOOK_URL, data=json.dumps(message), headers=headers)
    if response.status_code != 200:
        print(f"Error sending alert: {response.text}")


def lambda_handler(event, context):
    """
    AWS Lambda entry point.
    """
    # Step 1: Load feeds and keywords from S3
    config = load_config_from_s3(S3_BUCKET, S3_KEY)
    feeds = config.get("feeds", [])
    keywords = config.get("keywords", [])

    # Step 2: Process feeds concurrently
    results = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(process_feed, feed, keywords) for feed in feeds]
        for future in futures:
            results.append(future.result())

    # Step 3: Collect matches and send alerts
    alerts = [result for result in results if "matches" in result and result["matches"]]
    if alerts:
        send_alert(alerts)

    # Step 4: Generate summary
    summary = {
        "total_feeds_checked": len(feeds),
        "feeds_with_matches": len(alerts),
        "alerts_sent": len(alerts),
        "details": alerts
    }

    # Log summary for debugging
    print(json.dumps(summary, indent=4))

    return {
        "statusCode": 200,
        "body": json.dumps(summary)
    }
