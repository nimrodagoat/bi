# Setup guide (one time, about 20 minutes, all free)

You'll collect **4 secret values** and paste them into GitHub. After that,
everything runs by itself every day.

| Secret name | Where it comes from | Step |
|---|---|---|
| `PIXABAY_API_KEY` | pixabay.com (free stock videos) | 1 |
| `YT_CLIENT_ID` | Google Cloud | 3 |
| `YT_CLIENT_SECRET` | Google Cloud | 3 |
| `YT_REFRESH_TOKEN` | Google OAuth Playground | 4 |

> Keep these values private. Never paste them into a chat, a file in the repo,
> or anywhere public. They only go into GitHub Secrets (step 5).

---

## Step 1: Free Pixabay key (stock footage)

1. Go to **https://pixabay.com/** and click **Join** (create a free account; confirm your email).
2. While logged in, open **https://pixabay.com/api/docs/**.
3. Scroll to **Parameters** → `key (required)`: your personal key is shown there
   in green. Copy it. That's `PIXABAY_API_KEY`.

> Already have a Pexels API key? You can add it as `PEXELS_API_KEY` instead (or as well).
> Pexels currently isn't giving out new keys, which is why Pixabay is the default.
> No key at all? Videos still work, with an animated colour background.

## Step 2: Google Cloud project + YouTube API

Use the **same Google account that owns your YouTube channel**.

1. Go to **https://console.cloud.google.com/** and accept the terms if asked.
   No credit card is needed.
2. Top bar → project picker → **New project** → name it `shorts-autopilot` → **Create**.
   Make sure it's selected afterwards.
3. Search bar → **YouTube Data API v3** → **Enable**.

## Step 3: OAuth app (permission to upload)

1. Search bar → **Google Auth Platform** (or "OAuth consent screen") → **Get started**.
   - App name: `Shorts Autopilot`, support email: your email → Next
   - Audience: **External** → Next
   - Contact email: your email → Next → agree → **Create**
2. Left menu → **Branding** → fill in and **Save**:
   - Application home page: `https://github.com/nimrodagoat/bi`
   - Application privacy policy link: `https://github.com/nimrodagoat/bi/blob/HEAD/PRIVACY.md`
   - Authorized domains → **Add domain** → `github.com`
3. Left menu → **Audience** → click **Publish app** → Confirm.
   *(This is important: if the app stays in "Testing", your login expires every
   7 days and uploads stop.)*
4. Left menu → **Clients** → **Create client**
   - Application type: **Web application**
   - Name: `shorts`
   - Under **Authorized redirect URIs** → **Add URI** →
     `https://developers.google.com/oauthplayground`
   - **Create**
5. Copy the **Client ID** (`YT_CLIENT_ID`) and **Client secret** (`YT_CLIENT_SECRET`).

## Step 4: Get the refresh token (lets GitHub upload as you)

1. Open **https://developers.google.com/oauthplayground**
2. Click the **gear icon** (top right) → tick **Use your own OAuth credentials** →
   paste your Client ID and Client secret → close the panel.
3. In the left box **"Input your own scopes"**, paste:
   `https://www.googleapis.com/auth/youtube.upload` → **Authorize APIs**.
4. Sign in with the account that owns the channel. If you have several channels,
   **pick the channel you want to post to**.
5. You'll see "Google hasn't verified this app". That's expected, because it's your own
   app. Click **Advanced** → **Go to Shorts Autopilot (unsafe)** → **Continue / Allow**.
6. Back in the Playground, click **Exchange authorization code for tokens**.
7. Copy the **Refresh token**. That's `YT_REFRESH_TOKEN`.

## Step 5: Put the secrets into GitHub

1. Open this repository on GitHub → **Settings** → **Secrets and variables** → **Actions**.
2. Click **New repository secret** four times, once for each name in the table above.
   The names must match exactly.

## Step 6: Test run

1. GitHub → **Actions** tab → if asked, click **I understand… enable workflows**.
2. Click **Daily Short** → **Run workflow** → leave **"Test only"** ticked → **Run workflow**.
3. When it finishes (about 2–4 minutes), open the run → scroll to **Artifacts** →
   download `shorts-…` → unzip → watch the video.
4. Happy with it? Run it again with **"Test only" unticked**. The video is uploaded.
   Check YouTube Studio.

From now on it runs **every day by itself** (time is set in
`.github/workflows/daily-short.yml`).

## Step 7: Allow public videos (YouTube API audit; free, but takes time)

YouTube makes every video uploaded by a **new, unaudited API project private**.
Until the audit is approved:

- the daily upload still works, but each video arrives as **Private**;
- you can make it public by hand in YouTube Studio (one click per video).

To remove that limit, submit YouTube's free audit form:
**https://support.google.com/youtube/contact/yt_api_form** →
"YouTube API Services - Audit and Quota Extension Form". Describe it honestly:
*"Personal tool that uploads my own original Shorts to my own channel once a
day. Single user, no other users' data."* Approval usually takes days to a few weeks.

---

## Gameplay background (Minecraft parkour etc.)

By default every video gets **freshly generated Minecraft-style parkour** (a new
random course each time, made from scratch, so it's copyright-free). You don't
need to do anything for that.

If you'd rather use **your own recordings**, add them as below; they're then used
instead. Each Short uses a random part of a random video, so a few long
recordings (10+ minutes each) are plenty.

**Where to get footage you're allowed to use:**
- **Record it yourself.** Minecraft's rules allow videos of your own gameplay,
  including monetized ones. Free recorder: OBS Studio (obsproject.com).
  Record parkour, running, building: anything constantly moving.
- **Luanti** (luanti.org): a free, open-source Minecraft-like game you can record.
- Don't download other people's gameplay videos (e.g. "Subway Surfers gameplay"
  from YouTube). That's reuploading their content and leads to copyright claims.

**How to upload it (no size problems, free):**
1. On GitHub, open the repo → right side **Releases** → **Create a new release**.
2. **Choose a tag** → type `gameplay` → **Create new tag**. Title: `gameplay`.
3. Drag your .mp4 files into the box at the bottom (up to 2 GB each).
4. **Publish release**.

To add more later: Releases → `gameplay` → **Edit** → drag in more files → **Update release**.
Landscape (16:9) recordings are fine; the middle part is cropped to fill the vertical frame.

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| Run failed with `invalid_grant` | Refresh token expired. Check step 3.3 (app must be **published**), then redo step 4 and update `YT_REFRESH_TOKEN`. |
| `Missing secrets` | A secret name is misspelled in GitHub. |
| `The queue is empty` | Ask Claude for a new batch of scripts. |
| Background is a plain colour | `PIXABAY_API_KEY` is missing or wrong (the run log says why). |
| `quotaExceeded` | You uploaded more than ~6 videos today. It resumes tomorrow automatically. |
| GitHub emails you that a run failed | Open the run in the **Actions** tab, or paste the error to Claude. |
