# Vyral Labs — TikTok Video Downloader (MVP 1)

A simple web tool for downloading TikTok videos in HD without watermarks, organised by creator username.

## What it does

1. Paste a batch of TikTok URLs
2. Click Download All
3. Get a ZIP file with HD, watermark-free videos sorted into folders by username

```
tiktok_videos.zip
├── foodie_adventures/
│   ├── Amazing_recipe_7234567890.mp4
│   └── Best_pasta_ever_7234567891.mp4
└── travel_hacks/
    ├── Hidden_beach_7345678901.mp4
    └── Tokyo_street_food_7345678902.mp4
```

## Tech stack

- **Backend:** Python / Flask / yt-dlp
- **Frontend:** Vanilla HTML, CSS, JavaScript
- **Deployment:** Docker → Railway (or Render)

## Local development

```bash
# Install dependencies
pip install -r requirements.txt

# Run the server
python app.py
```

Then open [http://localhost:8000](http://localhost:8000).

## Deployment

See [DEPLOY.md](DEPLOY.md) for detailed step-by-step instructions (written for non-technical users).

## File structure

```
vyral-tiktok-downloader/
├── app.py              ← Backend server
├── requirements.txt    ← Python dependencies
├── Dockerfile          ← Docker config for deployment
├── .env.example        ← Environment variables template
├── .gitignore
├── static/
│   ├── index.html      ← Frontend page
│   ├── styles.css      ← Styles
│   └── script.js       ← Frontend logic
├── DEPLOY.md           ← Step-by-step deployment guide
└── README.md           ← This file
```

## How it works

1. Frontend sends a list of TikTok URLs to the backend API
2. Backend uses [yt-dlp](https://github.com/yt-dlp/yt-dlp) to download each video (HD, no watermark)
3. Videos are organised into folders by creator username
4. Everything gets zipped up and sent back to the browser
5. Frontend polls for progress and shows real-time status

## API endpoints

| Method | Endpoint                    | Description                          |
|--------|-----------------------------|--------------------------------------|
| GET    | `/`                         | Serves the frontend                  |
| POST   | `/api/download`             | Start a download job (body: `{urls}`) |
| GET    | `/api/status/<job_id>`      | Check job progress                   |
| GET    | `/api/download-zip/<job_id>`| Download completed ZIP file          |

## Out of scope (MVP 1)

- Auto-posting to Instagram/YouTube
- PostBridge integration
- Scheduling
- User accounts
- Database

These are planned for V2.
