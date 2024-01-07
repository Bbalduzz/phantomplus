<h1 align="center">
  Phantomplus
</h1>

<h4 align="center">Python Disney Plus API Metadata & Downloader for Windows, Macos and Linux</h4>

<p align="center">
  <a href="#features">Features</a> •
  <a href="#dependencies">Dependencies</a> •
  <a href="#how-to-use">How To Use</a>
</p>

## Features
* Get Metadata (title, year, episodes, seasons...) with official Disneyplus api
* Get medias (videos, audios, audio descriptions, subtitles...)
* Decrypt Widevine DRM protected content
* Automatically mux all your tracks
* Nice pre-made format for file names
* Very fast multi-connection downloads

## Dependencies
> make sure to add these in the PATH on in your working directory
- [ffmpeg](https://ffmpeg.org/)
- [aria2](https://github.com/aria2/aria2)
- [Bento4](https://www.bento4.com): mp4dump & mp4decrypt

## How to use
1. Obtain a Private L3 CDM (Content Decryption Module):
    - Option 1: Extract it yourself from an Android device using the [dumper](https://github.com/Diazole/dumper) tool.
    - Option 2: Purchase a private L3 CDM. For this, you can contact me on Telegram: [@edobal](https://t.me/edobal).

3. Setup the L3 CDM:
   - Place the L3 CDM files (device_client_id_blob, device_private_key) in the `private_l3_cdm`, inside the devices folder in your working environment.
  
Working folder example:
```bash
│   phantomplus/
│   └──pywidevine/
│      └──cdm/
│          └──devices/
│              └──private_l3_cdm/
│                   device_client_id_blob
│                   device_private_key
└─── main.py
```


Now open a terminal on the working dir and run:
- `pip install -r requirements.txt` 
- `py main.py`

## Demo
https://github.com/Bbalduzz/phantomplus/assets/81587335/2a49f72f-63ba-4b11-8e53-90dbf0e08e39

# Support
We also accept donations, so we can keep this project up!

[![liberapay](https://liberapay.com/assets/widgets/donate.svg)](https://liberapay.com/balduzz/donate)

[![ko-fi](https://ko-fi.com/img/githubbutton_sm.svg)](https://ko-fi.com/C0C8T2OJ6)

[![paypal](https://www.paypalobjects.com/en_US/i/btn/btn_donateCC_LG.gif)](https://www.paypal.com/donate/?hosted_button_id=3C8G7V8DUWLQG)
