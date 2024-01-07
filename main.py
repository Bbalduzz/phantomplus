from src.auth import DisneyPlusLogin
from src.api import DisneyPlusAPI
from src.parser import DisneyPlusParser
from src.m3u8_formatter import M3U8
from utils import utils
from pywidevine.decrypt.wvdecrypt import WvDecrypt

from collections import OrderedDict
from  pathlib import Path
import m3u8, requests, base64, os, shutil, subprocess, ffmpy, json, random

mp4decrypt = os.path.join(os.path.dirname(__file__), "bin", "macos" if os.name == "posix" else "windows", "mp4decrypt" if os.name == "posix" else "mp4decrypt.exe")
mp4dump = os.path.join(os.path.dirname(__file__), "bin", "macos" if os.name == "posix" else "windows", "mp4dump" if os.name == "posix" else "mp4dump.exe")
aria2c = "aria2c" if os.name == "posix" else os.path.join(os.path.dirname(__file__), "bin", "widows", "aria2c.exe")

def get_pssh(url):
	widevine_pssh = None
	m3u8_obj = m3u8.load(url)

	for key in m3u8_obj.keys:
		if key is not None and key.keyformat == "urn:uuid:edef8ba9-79d6-4ace-a3c8-27dcd51d21ed":
			widevine_pssh = key.uri

	if widevine_pssh is not None:
		widevine_pssh = widevine_pssh.partition('base64,')[2]

		return widevine_pssh
	return False

def do_decrypt(auth_token, pssh):
	wvdecrypt = WvDecrypt(pssh)
	challenge = wvdecrypt.get_challenge()
	resp = requests.post(
		url='https://disney.playback.edge.bamgrid.com/widevine/v1/obtain-license',
		headers={
			'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/77.0.3865.75 Safari/537.36',
			'Authorization': f'Bearer {auth_token}'
		},
		data=challenge
	)
	license_b64 = base64.b64encode(resp.content)
	wvdecrypt.update_license(license_b64)
	keys = wvdecrypt.start_process()[1]
	return keys

def download(url, output):
    txturls = output + '_links_.txt'
    baseurl = url.rsplit('/', 1)[0] + '/'
    manifest = requests.get(url).text
    dict_m3u8 = M3U8(manifest)
    media_segment = dict_m3u8.media_segment
    segments = []
    frags_path = []

    if 'MAIN' in manifest:
        for seg in media_segment:
            if seg.get('EXT-X-MAP') is not None and 'MAIN' in seg.get('EXT-X-MAP').get('URI'):
                segments.append(baseurl+seg.get('EXT-X-MAP').get('URI'))
                segments.append(baseurl+seg.get('URI'))
            if seg.get('EXT-X-MAP') is None and 'MAIN' in seg.get('URI'):
                segments.append(baseurl+seg.get('URI'))
    else:
        for seg in media_segment:
            if seg.get('EXT-X-MAP') is not None:
                segments.append(baseurl+seg.get('EXT-X-MAP').get('URI'))
                segments.append(baseurl+seg.get('URI'))
            if seg.get('EXT-X-MAP') is None:
                segments.append(baseurl+seg.get('URI'))

    segments = list(dict.fromkeys(segments))  # Remove duplicates


    txt = open(txturls,"w+")
    for i, s in enumerate(segments):
        name = "0" + str(i) + '.mp4'
        frags_path.append(name)
        txt.write(s + f"\n out={name}\n")
    txt.close()

    aria2c_command = [
        aria2c,
        f'--input-file={txturls}',
        '-x16',
        '-j16',
        '-s16',
        '--summary-interval=0',
        '--retry-wait=3',
        '--max-tries=10',
        '--enable-color=false',
        '--download-result=hide',
        '--console-log-level=error'
    ]

    subprocess.run(aria2c_command)

    runs = int(len(frags_path))
    openfile = open(output ,"wb")
    for run_num, fragment in enumerate(frags_path):
        if os.path.isfile(fragment):
            shutil.copyfileobj(open(fragment,"rb"),openfile)
        os.remove(fragment)
        utils.progress_bar(runs, run_num + 1, output)
    openfile.close()
    os.remove(txturls)
    print('Download and concatenation complete!')


def decryptmedia(keys, inputName, outputName):
	cmd = [mp4decrypt, *" ".join([f"--key {key}" for key in keys]).split(), inputName, outputName]
	wvdecrypt_process = subprocess.Popen(cmd)
	stdoutdata, stderrdata = wvdecrypt_process.communicate()
	wvdecrypt_process.wait()
	return True


def merge(input_video, input_audio, output_file):
	downloads_path = Path('downloads')
	if not downloads_path.is_dir(): downloads_path.mkdir()
	output_path = downloads_path / output_file
	ff = ffmpy.FFmpeg(
			inputs={input_video: None, input_audio: None},
			outputs={output_path: '-c:v copy -c:a copy'},
			global_options="-y -hide_banner -loglevel warning"
		)
	ff.run()
	return True

class DisneyPlusClient:
	def __init__(self, email, password, disney_id, language, media_type="movie", serie_season=0, episode=0, quality = 1080):
		self.email: str = email
		self.password: str = password
		self.disney_id: str = disney_id
		self.language: str = language
		self.media_type: str = media_type
		self.serie_season: int = serie_season
		self.season_episode: int = episode
		self.quality: int = quality

		login = DisneyPlusLogin(email=self.email, password=self.password)
		token, expire = login.get_auth_token()
		if self.media_type == "movie":
			dsnp = DisneyPlusAPI(dsny_id=self.disney_id, token=token, language=self.language, media_type=self.media_type)
			content = dsnp.load_playlist()
			title = content["title"]
		else:
			dsnp = DisneyPlusAPI(dsny_id=self.disney_id, token=token, language=self.language, media_type="show", season=self.serie_season, episode=self.season_episode)
			content = dsnp.load_playlist()
			title = f'{content["title"]}_S{self.serie_season}E{self.season_episode}'
		print(title)

		m3u8_url = dsnp.load_info_m3u8(content["id"]["mediaId"], content["mediaFormat"])
		load_manifest = DisneyPlusParser(m3u8_url["url"])
		video_list, audio_list, subtitle_list, forced_list, audio_extension = load_manifest.parse()
		print('[?] available audio: ',[audio['language'] for audio in audio_list])

		quality_available = [int(x['height']) for x in video_list]
		quality_available = list(OrderedDict.fromkeys(quality_available))
		print('[?] available qualities: ',quality_available)

		chosen_video_list = [x for x in video_list if int(x['height']) == int(self.quality)][0]
		input_video_name = 'temp_video__enc.mp4'
		decrypted_video_name = 'temp_video__dec.mp4'
		
		download(chosen_video_list["url"], input_video_name)
		for audio in audio_list:
			if audio['language'] == self.language.title():
				input_audio_name = 'temp_audio_' + audio['code'] + '_.mp4'
				download(url=audio['url'], output=input_audio_name)

		pssh = get_pssh(chosen_video_list["url"])
		keys = do_decrypt(token, pssh)
		print("[+] Decrypting media...")
		decryptmedia(keys, input_video_name, decrypted_video_name)
		print("[+] Merging video and audio...")
		merge(decrypted_video_name, input_audio_name, f'{content["title"]} [{self.quality}p].mp4')

		os.remove(input_audio_name)
		os.remove(decrypted_video_name)
		os.remove(input_video_name)

		print("[+] Done. Check", os.path.join(os.getcwd(), "downloads"))


# == run ==
# > this is downloading the 3th episide of thr 1st season
# DisneyPlusClient(
# 	email = "", # your email
# 	password = "", # your password
# 	disney_id = "ql33aq42HBdr", # disneyplus_id (last part of the url)
# 	language = "italian",
# 	media_type = "show",
# 	serie_season = 1,
# 	episode = 3,
# 	quality = 720 # max
# )
# > this is downloading a movie
DisneyPlusClient(
	email = " ", # your email
	password = " ", # your password
	disney_id = "1tmc3nPw04S2", # disneyplus_id (last part of the url)
	language = "italian",
	quality = 720 # max
)