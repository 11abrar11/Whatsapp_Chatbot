# Google Sheet Setup Guide

This guide walks you through setting up the Google Sheet for lead storage and the Google Cloud Service Account for API access.

---

## Step 1: Create the Google Sheet

1. Go to [Google Sheets](https://sheets.google.com)
2. Create a new blank spreadsheet
3. Rename it to **"PP5 WhatsApp Leads"** (or any name you prefer)
4. In **Row 1**, add these column headers (one per cell, A1 through Q1):

| Column | Header |
|--------|--------|
| A | Phone |
| B | Name |
| C | Business |
| D | Industry |
| E | Requirement |
| F | Monthly Leads |
| G | Company Size |
| H | Budget |
| I | Timeline |
| J | Decision Maker |
| K | Lead Score |
| L | Lead Status |
| M | Conversation Stage |
| N | Missing Information |
| O | Summary |
| P | Escalated |
| Q | Last Updated |

5. Copy the **Sheet ID** from the URL:
   ```
   https://docs.google.com/spreadsheets/d/SHEET_ID_IS_HERE/edit
   ```
   The Sheet ID is the long string between `/d/` and `/edit`

6. Paste this ID into your `config/.env` file as `GOOGLE_SHEET_ID`

---

## Step 2: Create a Google Cloud Service Account

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project (or select an existing one)
3. Enable the **Google Sheets API**:
   - Go to **APIs & Services** → **Enable APIs and Services**
   - Search for "Google Sheets API"
   - Click **Enable**
4. Enable the **Google Drive API** (also needed for sheet access):
   - Search for "Google Drive API"
   - Click **Enable**

---

## Step 3: Create Service Account Credentials

1. Go to **APIs & Services** → **Credentials**
2. Click **Create Credentials** → **Service Account**
3. Fill in:
   - **Name**: `pp5-chatbot-sheets`
   - **Description**: `Service account for WhatsApp chatbot Google Sheets access`
4. Click **Create and Continue**
5. For the role, select **Editor** (or skip this step)
6. Click **Done**
7. Click on the service account you just created
8. Go to the **Keys** tab
9. Click **Add Key** → **Create New Key**
10. Select **JSON** and click **Create**
11. A JSON file will be downloaded — this is your service account key

---

## Step 4: Place the Credentials File

1. Rename the downloaded JSON file to `service_account.json`
2. Move it to the `config/` directory in your project:
   ```
   WhatsApp Chatbot/
   └── config/
       ├── .env
       ├── .env.example
       └── service_account.json   ← place it here
   ```

---

## Step 5: Share the Sheet with the Service Account

1. Open the `service_account.json` file and find the `client_email` field:
   ```json
   {
     "client_email": "pp5-chatbot-sheets@your-project.iam.gserviceaccount.com"
   }
   ```
2. Go to your Google Sheet
3. Click **Share** (top-right)
4. Paste the `client_email` address
5. Set permission to **Editor**
6. Uncheck "Notify people"
7. Click **Share**

---

## Verification

After completing all steps, you should have:

- [ ] A Google Sheet with 17 column headers in Row 1
- [ ] The Sheet ID in your `config/.env` file
- [ ] `service_account.json` in the `config/` directory
- [ ] The sheet shared with the service account email as Editor

The chatbot will now be able to read and write lead data to this sheet.
