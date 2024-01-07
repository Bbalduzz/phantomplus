import json
import uuid
import requests
import base64
import pycountry


class DisneyPlusAPI:
    def __init__(self, dsny_id, token, media_type, language="english", season=None, episode=None):
        self.is_movie = media_type.lower() == 'movie'
        self.dsny_id = dsny_id
        self.token = token
        self.content_transaction_id = uuid.uuid4()
        self.season = None if self.is_movie else season
        self.episode = None if self.is_movie else episode
        self.language = pycountry.languages.get(name=language).alpha_2

        self.api_endpoints = {
            'DmcSeriesBundle': f'https://disney.content.edge.bamgrid.com/svc/content/DmcSeriesBundle/version/5.1/region/US/audience/false/maturity/1850/language/{self.language}/encodedSeriesId/{{video_id}}',
            'DmcEpisodes': f'https://disney.content.edge.bamgrid.com/svc/content/DmcEpisodes/version/5.1/region/US/audience/false/maturity/1850/language/{self.language}/seasonId/{{season_id}}/pageSize/30/page/1',
            'DmcVideo': f'https://disney.content.edge.bamgrid.com/svc/content/DmcVideoBundle/version/5.1/region/US/audience/false/maturity/1850/language/{self.language}/encodedFamilyId/{{family_id}}',
            'LicenseServer': 'https://edge.bamgrid.com/widevine/v1/obtain-license',
            'manifest': 'https://disney.playback.edge.bamgrid.com/v7/playback/ctr-limited'
        }

        self.scenarios = {
            "default": "restricted-drm-ctr-sw",
            "default_hevc": "handset-drm-ctr-h265",
            "SD": "handset-drm-ctr",
            "HD": "tv-drm-ctr",
            "atmos": "tv-drm-ctr-h265-hdr10-atmos",
            "uhd_sdr": "tv-drm-ctr-h265-atmos",
            "uhd_hdr": "tv-drm-ctr-h265-hdr10-atmos",
            "uhd_dv": "tv-drm-ctr-h265-dovi-atmos",
        }

    def _get_headers(self, extra_headers=None):
        headers = {
            "accept": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.82 Safari/537.36",
            "Sec-Fetch-Mode": "cors",
            "x-bamsdk-platform": "windows",
            "x-bamsdk-version": '3.10',
            "authorization": f'Bearer {self.token}'
        }
        if extra_headers: headers |= extra_headers
        return headers

    def load_info_m3u8(self, media_id, media_format, is_atmos=False):
        # NOTE: this has a sort of rate limiting
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:122.0) Gecko/20100101 Firefox/122.0',
            'Accept': 'application/vnd.media-service+json',
            'Accept-Language': 'en-US,en;q=0.5',
            # 'Accept-Encoding': 'gzip, deflate, br',
            'Referer': 'https://www.disneyplus.com/',
            'authorization': self.token,
            'content-type': 'application/json',
            'x-dss-feature-filtering': 'true',
            'x-application-version': '1.1.2',
            'x-bamsdk-client-id': 'disney-svod-3d9324fc',
            'x-bamsdk-platform': 'javascript/macosx/firefox',
            'x-bamsdk-version': '27.1',
            'x-dss-edge-accept': 'vnd.dss.edge+json; version=2',
            # 'x-request-id': '16556402-8fc2-45fa-905d-9894cbdd01bd',
            'Origin': 'https://www.disneyplus.com',
            # 'Connection': 'keep-alive',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'cross-site',
            'Pragma': 'no-cache',
            'Cache-Control': 'no-cache',
        }

        json_data = {
            'playback': {
                'attributes': {
                    'resolution': {'max': ['1280x720']}, # max res supported seems to be 720, but idk for sure
                    'protocol': 'HTTPS',
                    'assetInsertionStrategy': 'SGAI',
                    'playbackInitiationContext': 'ONLINE',
                    'frameRates': [60],
                    'slugDuration': 'SLUG_500_MS',
                },
                'adTracking': {
                    'limitAdTrackingEnabled': 'YES',
                    'deviceAdId': '00000000-0000-0000-0000-000000000000',
                },
                'tracking': {
                    'playbackSessionId': str(self.content_transaction_id),
                },
            },
            'playbackId': base64.b64encode(json.dumps({"mediaId": f"{media_id}"}).encode()).decode(),
        }

        if is_atmos:
            atmos_url = self.api_endpoints['manifest'].format(mediaid=media_id, scenarios=self.scenarios['uhd_hdr'])
            resp = requests.get(atmos_url, headers=headers)
            if resp.status_code != 200:
                print(f'M3U8 - Error: {resp.text}')
                return False
            atmos_data = json.loads(resp.text)
            atmos_stream_url = atmos_data['stream']['complete']

        url = self.api_endpoints['manifest']
        resp = requests.post(url=url, json=json_data, headers=headers)

        if resp.status_code != 200:
            print(f'M3U8 - Error: {resp.text}')
            return False

        data = json.loads(resp.text)
        m3u8_url = data['stream']["sources"][0]['complete']

        return (m3u8_url, atmos_stream_url) if is_atmos else m3u8_url

    def load_playlist(self):
        headers = self._get_headers()
        if self.is_movie:
            url = self.api_endpoints['DmcVideo'].format(family_id=self.dsny_id)
        else:
            url = self.api_endpoints['DmcSeriesBundle'].format(video_id=self.dsny_id)

        resp = requests.get(url=url, headers=headers)
        if resp.status_code != 200:
            print(f'DATA - Error: {resp.text}')
            return False
        data = resp.json()

        if self.is_movie:
            return self._process_movie_data(data)
        else:
            return self._process_episode_data(data)

    def _process_movie_data(self, data):
        data_info = data['data']['DmcVideoBundle']['video']
        title = data_info['text']['title']['full']['program']['default']['content']
        description = data_info['text']['description']['medium']['program']['default']['content']

        return {
            'title': title,
            'year': data_info['releases'][0]['releaseYear'],
            'description': description,
            'mediaFormat': data_info['mediaMetadata']['format'],
            'id': {
                'contentId': data_info['contentId'],
                'mediaId': data_info['mediaMetadata']['mediaId']
            }
        }

    def _process_episode_data(self, data):
        episode_list = []
        data_info = data['data']['DmcSeriesBundle']
        season_title = data_info['series']['text']['title']['full']['series']['default']['content']

        season = data_info['seasons']['seasons'][self.season - 1]
        season_content_id = season['seasonId']
        url = self.api_endpoints['DmcEpisodes'].format(season_id=season_content_id)
        resp = requests.get(url=url, headers=self._get_headers())
        if resp.status_code != 200:
            print(f'DATA - Error: {resp.text}')
            return False

        episodes_data = resp.json()['data']['DmcEpisodes']['videos']
        episode = episodes_data[self.episode - 1]
        return {
            'id': {
                'contentId': episode['contentId'],
                'mediaId': episode['mediaMetadata']['mediaId'],
            },
            'seasonNumber': episode['seasonSequenceNumber'],
            'episodeNumber': episode['episodeSequenceNumber'],
            'title': season_title,
            'mediaFormat': episode['mediaMetadata']['format']
        }

    def __get_serie_data(self, data):
        episode_list = []
        data_info = data['data']['DmcSeriesBundle']

        for season in data_info['seasons']['seasons']:
            if int(season['seasonSequenceNumber']) == int(self.season) :
                season_content_id = season['seasonId']

                url = self.api_endpoints['DmcEpisodes'].format(season_id=season_content_id)
                resp = requests.get(url=url, headers=self._get_headers())

                if resp.status_code != 200:
                    print(f'DATA - Error: {resp.text}')
                    return False

                episodes_data = resp.json()['data']['DmcEpisodes']['videos']

                for episode in episodes_data:
                    episode_dict = {
                        'contentId': episode['contentId'],
                        'mediaId': episode['mediaMetadata']['mediaId'],
                        'seasonNumber': episode['seasonSequenceNumber'],
                        'episodeNumber': episode['episodeSequenceNumber'],
                        'Title': season_title,
                        'mediaFormat': episode['mediaMetadata']['format']
                    }
                    episode_list.append(episode_dict)

        return episode_list
