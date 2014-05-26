import json
import re

from flask import Blueprint, request

from playlist.generator import PlaylistGenerator, ApiException, spotify_uri_to_url
from playlist.plthreading import generate_multiple_playlists_threaded
from playlist.rediscache import RedisPlaylistCache


api = Blueprint('api', __name__)


@api.route('/api/playlist', methods=['GET'])
def api_playlist():
    host = 'localhost'
    port = 6379
    database = 0
    password = None
    cache = RedisPlaylistCache(host, port, database, password)
    message = request.args.get('message')
    try:
        if message:
            messages = [sentence for sentence in re.split(r'[.?!/\n]', message) if len(sentence) > 0]
            if len(messages) > 1:
                # If we have multiple messages, process them concurrently
                playlist = []
                incomplete = False
                results = generate_multiple_playlists_threaded(messages, cache)
                for result in results:
                    if result[1]:
                        incomplete = True
                    playlist.extend(result[0])
            else:
                pl_gen = PlaylistGenerator(cache)
                playlist, incomplete = pl_gen.generate_playlist(messages[0])

            if playlist:
                generated_playlist = [{'name': item.name, 'uri': item.uri, 'url': spotify_uri_to_url(item.uri)} for item
                                      in playlist]
                payload = {'success': True, 'partial': incomplete, 'playlist': generated_playlist}
            else:
                payload = {'error': True, 'message': "Not able to generate playlist!"}
        else:
            payload = {'error': True, 'message': "No message provided!"}
    except ApiException as e:
        payload = {'error': True, 'message': "The Spotify API returned an error({})".format(str(e.status))}

    return json.dumps(payload)