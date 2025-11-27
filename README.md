# Padel Class Monitor - Automated GitHub Actions

This repository monitors the "Master Class With Oscar Marhuenda - Intermediate" padel class at G4P The Padel Yard and sends you notifications via IFTTT when new dates become available.

## 🚀 Setup Instructions

### 1. Create a GitHub Account (if you don't have one)
- Go to [github.com](https://github.com) and sign up for free

### 2. Create a New Repository
1. Click the "+" icon in top-right → "New repository"
2. Name it: `padel-monitor` (or anything you like)
3. Make it **Public** (required for free Actions)
4. ✅ Check "Add a README file"
5. Click "Create repository"

### 3. Add the Files to Your Repository

Create these 3 files in your repository (click "Add file" → "Create new file"):

#### File 1: `.github/workflows/monitor-padel.yml`
```yaml
# Copy the contents from the .github/workflows/monitor-padel.yml artifact
```

#### File 2: `check-padel.js`
```javascript
// Copy the contents from the check-padel.js artifact
```

#### File 3: `package.json`
```json
// Copy the contents from the package.json artifact
```

#### File 4: `known-dates.json`
```json
[]
```

### 4. Set Up IFTTT (for notifications)

1. **Get your IFTTT Webhook Key:**
   - Go to [ifttt.com/maker_webhooks](https://ifttt.com/maker_webhooks)
   - Click "Documentation"
   - Copy your key (looks like: `a1b2c3d4e5f6g7h8`)

2. **Create an IFTTT Applet:**
   - Go to [ifttt.com/create](https://ifttt.com/create)
   - **IF THIS**: Webhooks → "Receive a web request"
     - Event name: `padel_class_available`
   - **THEN THAT**: Choose your notification method:
     - **Email**: Sends to your email
     - **SMS**: Sends text message
     - **Notifications**: Push to IFTTT app
     - **Telegram/Discord/Slack**: Sends to chat
   - **Message Template** (example for email):
     ```
     Subject: 🎾 New Padel Class Dates Available!
     
     Body:
     {{Value1}} has new dates available:
     
     {{Value2}}
     
     Book now: {{Value3}}
     ```
   - Save the applet

### 5. Add Secrets to GitHub Repository

1. In your GitHub repository, go to **Settings** → **Secrets and variables** → **Actions**
2. Click "New repository secret"
3. Add two secrets:

   **Secret 1:**
   - Name: `IFTTT_WEBHOOK_KEY`
   - Value: Your IFTTT webhook key (from step 4.1)

   **Secret 2:**
   - Name: `IFTTT_EVENT_NAME`
   - Value: `padel_class_available` (or whatever event name you used)

### 6. Enable GitHub Actions

1. Go to the **Actions** tab in your repository
2. If prompted, click "I understand my workflows, go ahead and enable them"

### 7. Test It!

1. Go to **Actions** tab
2. Click on "Monitor Padel Classes" workflow
3. Click "Run workflow" → "Run workflow"
4. Wait 30-60 seconds and check the logs
5. You should receive a test notification via IFTTT!

## 📊 How It Works

- ✅ Runs automatically every 30 minutes
- ✅ Checks the Matchi website for new class dates
- ✅ Compares with previously known dates (stored in `known-dates.json`)
- ✅ Sends IFTTT notification when new dates appear
- ✅ Updates the known dates file
- ✅ Completely free and automated

## 🔧 Customization

### Change Check Frequency
Edit `.github/workflows/monitor-padel.yml`:
```yaml
schedule:
  - cron: '*/30 * * * *'  # Every 30 minutes
  # - cron: '*/15 * * * *'  # Every 15 minutes
  # - cron: '0 * * * *'     # Every hour
  # - cron: '0 */2 * * *'   # Every 2 hours
```

### Monitor Different Activity
Edit `check-padel.js`:
```javascript
const ACTIVITY_NAME = 'Master Class With Oscar Marhuenda - Intermediate';
// Change to any other activity name
```

## 📝 Monitoring Logs

- Go to **Actions** tab to see all runs
- Click on any run to see detailed logs
- Each log shows:
  - How many dates were found
  - Whether new dates were detected
  - Whether notifications were sent

## ⚠️ Troubleshooting

### No notifications received?
1. Check Actions tab for errors
2. Verify IFTTT webhook key is correct in Secrets
3. Test your IFTTT applet manually
4. Check IFTTT applet is turned ON

### Workflow not running?
1. Repository must be **Public** for free Actions
2. Check Actions tab is enabled
3. Manually trigger via "Run workflow" button

### "Activity not found" error?
- The website structure may have changed
- The activity may be temporarily unavailable
- Check the URL is still correct

## 💰 Cost

**100% FREE** - GitHub Actions provides:
- 2,000 minutes/month for public repositories
- This workflow uses ~1 minute per run
- Running every 30 minutes = ~1,440 runs/month
- Well within free tier!

## 🎉 You're All Set!

Your monitor will now check automatically every 30 minutes and notify you when new padel class dates become available. Book fast! 🏃‍♂️💨
