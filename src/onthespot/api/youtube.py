import json
import os
from hashlib import md5
from yt_dlp import YoutubeDL
from ..otsconfig import config
from ..runtimedata import get_logger, account_pool

logger = get_logger("api.youtube")


def youtube_login_user(account):
    if account['uuid'] == 'public_youtube':
        account_pool.append({
            "uuid": "public_youtube",
            "username": 'yt-dlp',
            "service": "youtube",
            "status": "active",
            "account_type": "public",
            "bitrate": "256k",
        })
        return True


def youtube_add_account():
    cfg_copy = config.get('accounts').copy()
    new_user = {
            "uuid": "public_youtube",
            "service": "youtube",
            "active": True,
        }
    cfg_copy.append(new_user)
    config.set_('accounts', cfg_copy)
    config.update()


def youtube_get_search_results(_, search_term, content_types):
    ydl_opts = {
        'quiet': True,
        'extract_flat': True,
    }

    search_results = []
    if 'track' in content_types:
        with YoutubeDL(ydl_opts) as ytdl:
            result = ytdl.extract_info(f'ytsearch{config.get("max_search_results")}:{search_term}', download=False)
            for result in result['entries']:
                search_results.append({
                    'item_id': result['id'],
                    'item_name': result['title'],
                    'item_by': result['channel'],
                    'item_type': "track",
                    'item_service': "youtube",
                    'item_url': result['url'],
                    'item_thumbnail_url': f'https://i.ytimg.com/vi/{result["id"]}/hqdefault.jpg'
                })

    logger.debug(search_results)
    return search_results


def youtube_get_track_metadata(_, item_id):
    url = f'https://music.youtube.com/watch?v={item_id}'
    request_key = md5(f'{url}'.encode()).hexdigest()
    cache_dir = os.path.join(config.get('_cache_dir'), 'reqcache')
    os.makedirs(cache_dir, exist_ok=True)
    req_cache_file = os.path.join(cache_dir, request_key + '.json')

    if os.path.isfile(req_cache_file):
        logger.debug(f'URL "{url}" cache found ! HASH: {request_key}')
        with open(req_cache_file, 'r', encoding='utf-8') as cf:
            info_dict = json.load(cf)

    else:
        info_dict = YoutubeDL({'quiet': True}).extract_info(url, download=False)
        json_output = json.dumps(info_dict, indent=4)
        with open(req_cache_file, 'w', encoding='utf-8') as cf:
            cf.write(json_output)

    # Convert length to milliseconds
    timestamp = info_dict.get('duration_string', '')
    if timestamp:
        parts = timestamp.split(':')
        if len(parts) == 3:
            hours, minutes, seconds = map(int, parts)
            total_seconds = (hours * 3600) + (minutes * 60) + seconds
        elif len(parts) == 2:
            minutes, seconds = map(int, parts)
            total_seconds = (minutes * 60) + seconds
        length = total_seconds * 1000
    else:
        length = ''

    info = {}
    info['title'] = info_dict.get('title', '')
    album = info_dict.get('album', '')
    info['album_name'] = album if album else info_dict.get('title', '')
    info['artists'] = info_dict.get('channel', '')
    info['album_artists'] = info_dict.get('channel', '')
    info['description'] = info_dict.get('description', '')
    # Commented thumbnails are periodically missing
    #info['image_url'] = info_dict.get('thumbnail', '')
    #info['image_url'] = f'https://i.ytimg.com/vi/{item_id}/maxresdefault.jpg'
    info['image_url'] = f'https://i.ytimg.com/vi/{item_id}/hqdefault.jpg'
    info['language'] = info_dict.get('language', '')
    info['item_url'] = info_dict.get('webpage_url', '')
    # Windows takes issue with the following line, not sure why
    #info['release_year'] = info_dict.get('release_date', '')[:4] #20150504
    release_year = info_dict.get('release_year', '')
    info['release_year'] = str(release_year if release_year else info_dict.get('upload_date', '')[:4])
    info['length'] = length
    info['is_playable'] = True if info_dict.get('availability', '') == 'public' and not info_dict.get('is_live', '') else False
    info['item_id'] = item_id

    return info


def youtube_get_playlist_data(_, playlist_id):
    url = f'https://music.youtube.com/playlist?list={playlist_id}'
    ydl_opts = {
        'quiet': True,
        'extract_flat': True,
    }

    with YoutubeDL(ydl_opts) as ytdl:
        playlist_data = ytdl.extract_info(url, download=False)

    playlist_name = playlist_data.get('title', '')
    playlist_by = playlist_data.get('channel', '') # If null the item is an album

    track_ids = []
    for entry in playlist_data['entries']:
        track_ids.append(entry.get('id', ''))
    return playlist_name, playlist_by, track_ids


def youtube_get_channel_track_ids(_, channel_id):
    url = f'https://music.youtube.com/channel/{channel_id}'

    ydl_opts = {
        'quiet': True,
        'extract_flat': True,
    }

    with YoutubeDL(ydl_opts) as ytdl:
        channel_data = ytdl.extract_info(url, download=False)

    track_ids = []
    for entry in channel_data['entries']:
        track_ids.append(entry.get('id', ''))
    return track_ids
