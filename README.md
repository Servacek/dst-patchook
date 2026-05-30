# Patchook
A Discord webhook implementation for posting updates from Klei forums.

![image](https://github.com/Servacek/Patchook/assets/105163129/fe9017d2-3ab9-4a7d-b9f2-a3743f28f150)

## Features

### 1. Automatic Tags
In case of a forum webhook, it will automatically apply the tags configured for each update category to the thread upon creation.

![image](https://github.com/Servacek/Patchook/assets/105163129/91767b06-8aba-493d-b81d-cb56b82727a7)

### 2. Detecting Reward Links
Reward links for free Klei points or Spools will be automatically detected and displayed in the link section of the post.

![image](https://github.com/Servacek/Patchook/assets/105163129/103ca93e-877f-4654-a995-1b615938aca3)

### 3. Thumbnails
In case the update description contains any images or videos, the first one will be used as a thumbnail to the thread.

### 4. Extended Description Limits
Embeds sent by the webhook have description lenght limit up to 6000 characters instead of the default 4096 thanks to utilizing the embed fields.
This enables the webhook to display most of the big updates without cropping the content.

### 5. Support for Text and Forum channels
For each webhook configured you can set whether it's a forum webhook or a default one.
Forum webhooks will create a new thread for each of the updates where people can discuss the changes separately.
Default webhooks will just post the embed in the channel they are integrated in.

### 6. Application Owned Webhooks
If the webhook configured was created by a bot and marked as so in `config.json`, it will use link buttons instead of hyperlinks.

## Used By

Patchook is actively keeping players up to date with the newest changes in the game in these communities:

[![Don't Fight Together](https://invidget.switchblade.xyz/phewTaz)](https://discord.gg/phewTaz)
[![[CZ/SK] Don't Starve](https://invidget.switchblade.xyz/RHzJxut)](https://discord.gg/RHzJxut)

## Dependencies
- Python v3.10 or higher
- beautifulsoup4 v4.12.3
- requests v2.32.3
- python-dateutil v2.9.0

## Setup

Start by creating `config.json` in the [`data`](https://github.com/Servacek/dst-patchook/tree/main/data) folder and configuring your webhooks as shown in [`example_config.json`](https://github.com/Servacek/dst-patchook/blob/main/data/example_config.json).

Then pick one of the two methods below to run Patchook.

![image](https://github.com/Servacek/dst-patchook/assets/105163129/0fdd66d7-8dd7-4165-8711-488be5a42f1a)

### Option A — Virtual Environment (Python 3.10+)

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# Linux / macOS
source .venv/bin/activate

pip install -r requirements.txt
python src/main.py
```

Schedule periodic runs using `crontab`, `systemd` timers, Task Scheduler, or any other alternative so Patchook checks for updates automatically.

### Option B — Docker

```bash
# Build the image
docker build -t patchook .

# Run once
docker run --rm -v "$(pwd)/data:/app/data" patchook
```

The `-v` flag mounts your local `data/` folder into the container so `config.json` and any persisted state survive between runs.

To run Patchook on a schedule, use a cron job or `systemd` timer to execute the `docker run` command periodically.
