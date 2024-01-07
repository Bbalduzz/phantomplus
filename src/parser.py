import requests
import re
import sys
import pycountry
from src.m3u8_formatter import M3U8

language_codes = {
    "zh-Hans": "zhoS",
    "zh-Hant": "zhoT",
    "pt-BR": "brPor",
    "es-ES": "euSpa",
    "en-GB": "enGB",
    "en-PH": "enPH",
    "nl-BE": "nlBE",
    "fil": "enPH",
    "yue": "zhoS",
    'fr-CA': 'caFra'
}


class DisneyPlusParser:
    def __init__(self, m3u8_url, atmos_m3u8_url=None, is_2ch=False):
        self.m3u8_url = m3u8_url
        self.base_url = self.m3u8_url.rsplit('/', 1)[0] + '/'
        self.is_atmos = atmos_m3u8_url is not None
        self.atmos_m3u8_url = atmos_m3u8_url
        self.atmos_base_url = self.atmos_m3u8_url.rsplit('/', 1)[0] + '/' if self.is_atmos else None
        self.is_2ch = is_2ch

    def get_country_code(self, code):
        if code in ['cmn-Hans', 'cmn-Hant', 'es-419', 'es-ES', 'pt-BR', 'pt-PT', 'fr-CA', 'fr-FR']:
            translations = {
                'cmn-Hans': ('Mandarin Chinese (Simplified)', 'zh-Hans'),
                'cmn-Hant': ('Mandarin Chinese (Traditional)', 'zh-Hant'),
                'es-419': ('Spanish', 'spa'),
                'es-ES': ('European Spanish', 'euSpa'),
                'pt-BR': ('Brazilian Portuguese', 'brPor'),
                'pt-PT': ('Portuguese', 'por'),
                'fr-CA': ('French Canadian', 'caFra'),
                'fr-FR': ('French', 'fra')
            }
            return translations[code]

        lang_code = code.split('-')[0]
        lang = pycountry.languages.get(alpha_2=lang_code) or pycountry.languages.get(alpha_3=lang_code)
        try:
            language_code = language_codes[code]
        except KeyError:
            language_code = lang.alpha_3

        return lang.name, language_code

    def get_codec(self, codecs):
        search = 'hvc' if is_hevc or is_hdr or is_hdrdv else 'avc'
        filtered_codecs = [c for c in codecs.split(',') if search in c]
        return filtered_codecs[-1] if filtered_codecs else None

    def parse(self):
        video_list, audio_list, subtitle_list, forced_list = [], [], [], []
        added = set()

        video_manifest = self._fetch_manifest(self.m3u8_url)
        audio_manifest = self._fetch_manifest(self.m3u8_url)
        audio_base = self.base_url
        audio_text = requests.get(self.m3u8_url).text

        if 'eac-3' in str(audio_text):
            audio_codecs = 'eac-3'
            audio_extension = '.eac3'
        else:
            print('this item has no ac3 6ch, trying aac 2ch')
            if 'aac-128k' in str(audio_text):
                audio_codecs = 'aac-128k'
                audio_extension = '.aac'
            else:
                print('this item has no aac 2ch')
                sys.exit(1)

        if audio_codecs is None or audio_extension is None:
            print('error while search for audio codec in m3u8 streams.')
            sys.exit(1)


        video_streams = [x for x in video_manifest.master_playlist if x['TAG'] == 'EXT-X-STREAM-INF']
        audio_streams = [x for x in audio_manifest.master_playlist if x['TAG'] == 'EXT-X-MEDIA']
        subs_streams = [x for x in video_manifest.master_playlist if x['TAG'] == 'EXT-X-MEDIA']

        for video in video_streams:
            if not video["URI"] in added:
                bitrate = 'None'
                if re.search('([0-9]*)k_', video["URI"]):
                    bitrate = str(re.search('([0-9]*)k_', video["URI"])[1])
                else:
                    if re.search('([0-9]*)_complete', video["URI"]):
                        bitrate = str(re.search('([0-9]*)_complete', video["URI"])[1])

                video_list.append(
                            {
                                'resolution': video["RESOLUTION"],
                                'codec': str(video["CODECS"]),
                                'bandwidth': str(video["BANDWIDTH"]),
                                'bitrate': bitrate,
                                'height': video["RESOLUTION"].rsplit('x', 1)[1],
                                'url': self.base_url+video["URI"]
                            }
                        )
                added.add(video["URI"])

        for m in audio_streams:
            if m['TYPE'] == 'AUDIO' and m['GROUP-ID'] == audio_codecs and m.get('CHARACTERISTICS') is None:
                bitrate = 'None'
                if re.search('([0-9]*)k_', m["URI"]):
                    bitrate = str(re.search('([0-9]*)k_', m["URI"])[1])
                else:
                    if re.search('([0-9]*)_complete', m["URI"]):
                        bitrate = str(re.search('([0-9]*)_complete', m["URI"])[1])

                bitrate = '768' if str(m['CHANNELS']) == '16/JOC' and int(bitrate) > 768 else bitrate
                language, code = self.get_country_code(m['LANGUAGE'])
                
                Profile = m['GROUP-ID']
                Profile = "aac" if "aac" in m['GROUP-ID'].lower() else Profile
                Profile = "eac-3" if "eac-3" in m['GROUP-ID'].lower() else Profile
                Profile = "atmos" if "joc" in m['GROUP-ID'].lower() else Profile

                audio_list.append(
                        {
                            'language': str(language),
                            'code': str(code),
                            'bitrate': bitrate,
                            'codec': Profile,
                            'channels': str(m['CHANNELS'].replace('"', "").replace("/JOC", "")),
                            'url': audio_base+m['URI']
                        }
                    )

        for m in subs_streams:                    
            if m['TYPE'] == 'SUBTITLES' and m['FORCED'] == 'NO':
                language, code = self.get_country_code(m['LANGUAGE'])
                subtitle_list.append(
                        {
                            'language': str(language),
                            'code': str(code),
                            'url': self.base_url+m['URI']
                        }
                    )

            if m['TYPE'] == 'SUBTITLES' and m['FORCED'] == 'NO' and m['LANGUAGE'] == 'en':
                language, code = self.get_country_code(m['LANGUAGE'])
                subtitle_list.append(
                        {
                            'language': str(language),
                            'code': 'sdh-' + str(code),
                            'url': self.base_url+m['URI']
                        }
                    )

            if m['TYPE'] == 'SUBTITLES' and m['FORCED'] == 'YES':
                language, code = self.get_country_code(m['LANGUAGE'])
                forced_list.append(
                        {
                            'language': str(language),
                            'code': str(code),
                            'url': self.base_url+m['URI']
                        }
                    )

        video_list = sorted(video_list, key=lambda k: int(k['bandwidth']))
        return video_list, audio_list, subtitle_list, forced_list, audio_extension

    def _fetch_manifest(self, url):
        response = requests.get(url)
        return M3U8(response.text)
