# LLM-Stock-Prediction

This project is a simulation to the question to what extent does prompt phrasing affect the accuracy of short term stock predictions on ChatGpt-5.

## Setup Instructions

### Environment Variables (Railway)

1. **OPENAI_API_KEY**: Your OpenAI API key
2. **GMAIL_APP_PASSWORD**: Your Gmail App Password (see below)

### Gmail App Password Setup

To enable email notifications, you need to create a Gmail App Password:

1. Go to your Google Account settings: https://myaccount.google.com/
2. Navigate to **Security** → **2-Step Verification** (enable if not already enabled)
3. Scroll down to **App passwords**
4. Select **Mail** and **Other (Custom name)**
5. Enter "Railway Stock Predictions" as the name
6. Click **Generate**
7. Copy the 16-character password (no spaces)
8. Add it to Railway as `GMAIL_APP_PASSWORD` environment variable

### Email Notifications

- Daily emails sent after each trading day with `predictions.xlsx` attached
- Final report email sent on Feb 1st with `final_report_feb1.xlsx` attached
- Emails sent to: aadityasai.kalyankar@gmail.com
