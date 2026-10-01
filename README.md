# The Sponsor's Playbook

A private podcast that publishes one 15-minute private equity lesson every weekday morning. Claude writes the script, a TTS voice records it, and Apple Podcasts downloads it before you leave for work.

**Schedule:** Monday to Friday, 5:00 a.m. Eastern (4:00 a.m. in winter). GitHub can run scheduled jobs up to about an hour late, so this still lands well before a morning drive.

**Course:** 60 lessons in 6 modules, foundations first, advanced structures last. Edit `curriculum.py` to change topics or order.

---

## Setup (about 20 minutes, one time)

### 1. Get two API keys

| Key | Where | Notes |
|---|---|---|
| Anthropic | console.anthropic.com > API Keys | Add a payment method. Writes the scripts. |
| OpenAI | platform.openai.com > API Keys | Add a payment method. Records the audio. |

Using Google or ElevenLabs for the voice instead? See "Change the voice" below.

### 2. Create the GitHub repo

1. On github.com, create a new repository named `sponsors-playbook`. Set it to **Public** (free GitHub Pages hosting requires it).
2. Upload every file in this folder, keeping the `.github/workflows` folder structure intact. Easiest: drag the unzipped folder contents into the "uploading an existing file" page, then commit.

### 3. Add your keys as secrets

Repo > **Settings > Secrets and variables > Actions > New repository secret**

| Name | Value |
|---|---|
| `ANTHROPIC_API_KEY` | your Anthropic key |
| `OPENAI_API_KEY` | your OpenAI key |
| `LISTENER_CONTEXT` | Optional. A sentence about your role so examples fit your world, e.g. *COO and General Counsel at a U.S. freight brokerage.* Stored as a secret so it isn't visible in the public repo. |

### 4. Turn on hosting

Repo > **Settings > Pages > Build and deployment > Source: GitHub Actions**

### 5. Publish lesson 1

Repo > **Actions > Daily lesson > Run workflow > Run workflow**

Takes 3 to 5 minutes. When the run shows a green check, your feed is live at:

```
https://YOUR-GITHUB-USERNAME.github.io/sponsors-playbook/feed.xml
```

(Username in lowercase. You can also open `https://YOUR-GITHUB-USERNAME.github.io/sponsors-playbook/` in a browser to see episodes and transcripts.)

### 6. Subscribe on your iPhone

1. Open **Podcasts > Library**.
2. Tap **⋯** (top right) > **Follow a Show by URL**, paste the feed URL, tap **Follow**.
3. Open the show > **⋯ > Settings**: turn **Automatically Download** on.

### 7. In the car

Open Podcasts on CarPlay, or say **"Hey Siri, play The Sponsor's Playbook."** Because the show is set up as a serial, it plays in lesson order. New episodes appear each weekday morning with no action from you.

---

## Everyday controls

| Want to... | Do this |
|---|---|
| Redo a lesson (new script and audio) | Actions > Daily lesson > Run workflow, enter the lesson number |
| Get an extra lesson today | Run workflow with the lesson box blank |
| Pause the show | Actions > Daily lesson > **⋯ > Disable workflow** |
| Change topics | Edit `curriculum.py` in GitHub. Unpublished lessons pick up the change. |
| Change listener context | Update the `LISTENER_CONTEXT` secret |

If a run fails (API outage, expired key), GitHub emails you. Fix the cause and click **Re-run jobs**.

---

## Change the voice

Set these under **Settings > Secrets and variables > Actions > Variables** (variables, not secrets):

| Variable | Options |
|---|---|
| `TTS_PROVIDER` | `openai` (default), `google`, `elevenlabs` |
| `TTS_VOICE` | Voice name or ID for that provider (see below) |
| `TTS_MODEL` | Optional model override |
| `CLAUDE_MODEL` | Optional. Defaults to `claude-sonnet-5-5`. |

**OpenAI** (default, `gpt-4o-mini-tts`). Voice defaults to `onyx`. Others to try: `ash`, `echo`, `sage`, `coral`, `ballad`. The script also sends a "podcast host" delivery style, which noticeably improves pacing. Preview voices at openai.fm.

**Google Cloud Text-to-Speech.** In Google Cloud Console, enable the Text-to-Speech API, create an API key, save it as secret `GOOGLE_TTS_API_KEY`, set `TTS_PROVIDER` to `google`. Voice defaults to `en-US-Chirp3-HD-Charon`.

**ElevenLabs.** Save your key as secret `ELEVENLABS_API_KEY`, set `TTS_PROVIDER` to `elevenlabs`, and set `TTS_VOICE` to a voice ID from your ElevenLabs Voice Library (defaults to "George"). Uses `eleven_flash_v2_5` by default. Note the monthly volume below against your plan's credits.

To hear a new voice on an old lesson, change the variable and redo that lesson number.

---

## Cost

About 20 to 22 lessons a month, each roughly 12,000 to 13,000 characters of script.

- **Claude:** a few cents per lesson.
- **Voice:** OpenAI and Google typically run single-digit dollars a month at this volume. ElevenLabs depends on plan and model; check your plan's monthly credits against about 275,000 characters.
- **GitHub:** free.

Set a monthly spend limit in both the Anthropic and OpenAI consoles for peace of mind.

---

## Privacy note

The repo and feed are public but unlisted: the feed is blocked from podcast directories (`itunes:block`) and the web page is marked noindex. Anyone who has the URL can listen. Your listener context stays in a secret and never appears in the repo, though lessons may reference your industry. If you want the repo itself private, GitHub Pro ($4/month) allows Pages from a private repo.

---

## Files

| File | Purpose |
|---|---|
| `podcast.py` | Writes the script, records audio, rebuilds the feed |
| `curriculum.py` | The 60 lessons |
| `.github/workflows/daily-lesson.yml` | Weekday schedule and publishing |
| `data/episodes.json` | What's been published (updated automatically) |
| `docs/` | Feed, episodes, transcripts, cover art (created automatically) |

Local test without spending on audio: `pip install -r requirements.txt`, set `ANTHROPIC_API_KEY`, run `python podcast.py --script-only`.
