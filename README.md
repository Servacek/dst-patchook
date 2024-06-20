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

## Dependencies
- Python v3.10 or higher
- beautifulsoup4 v4.12.3
- requests v2.32.3

## Setup
1. Download dependencies from [`requirements.txt`](https://github.com/Servacek/dst-patchook/blob/main/requirements.txt) using `pip install -r requiremnets.txt`
1. Configure your webhooks using config.json as shown in `example_config.json`.
2. Setup a task (using crontab or systemd timers, or any other way) which will every once in a while trigger main.py and check for the updates.

