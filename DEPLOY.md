# Deployment Guide — Vyral Labs TikTok Downloader

This guide walks you through putting the downloader online so Hannah (or anyone on your team) can use it from a browser. **No terminal experience required** — just follow each step exactly.

---

## Overview

You'll do three things:

1. **Upload the code to GitHub** (a site that stores code)
2. **Connect GitHub to Railway** (a site that runs the code as a live website)
3. **Get your URL** and start using it

Total time: ~15 minutes.

---

## Step 1 — Create a GitHub account (skip if you already have one)

1. Go to [github.com](https://github.com) and click **Sign up**.
2. Follow the prompts — use any email and pick a username.
3. Verify your email.

## Step 2 — Upload the code to GitHub

### Option A: Upload via the GitHub website (easiest — no terminal needed)

1. Sign in to [github.com](https://github.com).
2. Click the **+** icon in the top-right corner → **New repository**.
3. Name it `vyral-tiktok-downloader`.
4. Leave it as **Public** (Railway needs to see it).
5. **Do NOT** tick "Add a README file" — the project already has one.
6. Click **Create repository**.
7. On the next page, you'll see a quick setup screen. Click the link that says **"uploading an existing file"**.
8. Drag and drop **all the project files and folders** into the upload area:
   - `app.py`
   - `requirements.txt`
   - `Dockerfile`
   - `.env.example`
   - `.gitignore`
   - `README.md`
   - `DEPLOY.md`
   - The entire `static/` folder (with `index.html`, `styles.css`, `script.js` inside)
9. Scroll down, leave the commit message as-is, and click **Commit changes**.

> **Important:** Make sure the `static` folder and its three files are uploaded. Without them, the website won't have a user interface.

### Option B: Upload via the terminal (if you're comfortable with it)

```bash
cd vyral-tiktok-downloader
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/YOUR_USERNAME/vyral-tiktok-downloader.git
git branch -M main
git push -u origin main
```

---

## Step 3 — Create a Railway account

1. Go to [railway.app](https://railway.app).
2. Click **Login** → **Login with GitHub**.
3. Authorise Railway to access your GitHub account.
4. You may need to add a payment method (Railway's free trial gives you $5 of credit, which lasts ages for this tool — roughly $5/month after that).

---

## Step 4 — Deploy to Railway

1. Once logged in to Railway, click **New Project**.
2. Click **Deploy from GitHub repo**.
3. Select the `vyral-tiktok-downloader` repository from the list.
   - If you don't see it, click **Configure GitHub App** and give Railway access to the repo.
4. Railway will automatically detect the Dockerfile and start building. You'll see a build log — this takes 2-3 minutes.
5. While it builds, click on the service (the purple box), then go to the **Settings** tab.
6. Scroll down to **Networking** and click **Generate Domain**. This gives you a public URL like `vyral-tiktok-downloader-production.up.railway.app`.
7. Wait for the build to finish (you'll see a green "Success" status).
8. Click your generated URL — you should see the Vyral Labs TikTok Downloader page!

### Environment Variables (optional)

Railway sets the `PORT` variable automatically. But if you want to change the max videos per batch:

1. In your Railway service, go to the **Variables** tab.
2. Click **New Variable**.
3. Add: `MAX_VIDEOS_PER_BATCH` = `50` (or whatever number you want).
4. Click **Add** — the service will automatically redeploy.

---

## Step 5 — Use it!

1. Open the URL Railway gave you in any browser.
2. Paste TikTok URLs (one per line) into the text box.
3. Click **Download All**.
4. Wait for all videos to finish downloading.
5. Click **Download ZIP** to save the file to your computer.
6. Unzip the file — videos are sorted into folders by creator username.

---

## Troubleshooting

### "The page won't load"
- Go to Railway → your project → check the service status. If it says "Crashed", click on the **Logs** tab to see the error.
- Make sure the domain is generated (Settings → Networking → Generate Domain).

### "Videos fail to download"
- TikTok sometimes blocks downloads temporarily. Try again in a few minutes.
- Private videos or deleted videos can't be downloaded.
- If ALL videos fail, yt-dlp might need updating (see below).

### "ZIP file is empty"
- This happens when every video in the batch failed. Check the error messages next to each URL and try different URLs.

### How to update yt-dlp (if downloads start failing)

TikTok occasionally changes their internal APIs, which can break yt-dlp. The fix is usually to update yt-dlp:

1. Go to your Railway project.
2. Click **Settings** on your service.
3. Scroll down to find **Restart** and click it — Railway rebuilds from the Dockerfile, which always installs the latest yt-dlp.

If that doesn't fix it:
1. Open `requirements.txt` in your GitHub repo (click the file → pencil icon to edit).
2. Change the yt-dlp line to force a newer minimum version, e.g.:
   ```
   yt-dlp>=2025.1.0
   ```
3. Commit the change — Railway will automatically redeploy with the new version.

---

## Alternative: Deploy to Render (instead of Railway)

If you prefer Render:

1. Go to [render.com](https://render.com) and sign up with GitHub.
2. Click **New** → **Web Service**.
3. Connect your `vyral-tiktok-downloader` repo.
4. Settings:
   - **Environment:** Docker
   - **Instance Type:** Starter ($7/month) — the free tier spins down after inactivity which causes slow first loads
5. Click **Create Web Service**.
6. Wait for the build (3-5 minutes).
7. Render gives you a URL like `vyral-tiktok-downloader.onrender.com`.

---

## Cost Summary

| Service  | Cost          | Notes                                    |
|----------|---------------|------------------------------------------|
| GitHub   | Free          | Hosting the code                         |
| Railway  | ~$5/month     | Running the server ($5 free trial credit)|
| yt-dlp   | Free          | Open-source TikTok downloader            |
| **Total**| **~$5/month** |                                          |

---

## Need Help?

If something breaks and you can't figure it out, the most useful thing to share is:

1. A screenshot of the Railway **Logs** tab (shows what went wrong on the server).
2. A screenshot of the error message in the browser (if any).
3. The TikTok URLs you were trying to download.
