"""Shared helper for converting spotify:type:id URIs to open.spotify.com sharelinks.

Used by both JukeBoxSonosProd.py (actual playback) and web_manager.py
(play-test button and URI validation) so the two stay in agreement about
what counts as a playable URI.
"""

VALID_KINDS = ('album', 'playlist', 'track')

def uri_to_sharelink(spotify_uri):
    """Convert a spotify:type:id URI into an open.spotify.com sharelink.
    Returns None if the URI doesn't match the expected format."""
    parts = spotify_uri.split(':')
    if len(parts) != 3 or parts[0] != 'spotify' or parts[1] not in VALID_KINDS:
        return None
    return f"https://open.spotify.com/{parts[1]}/{parts[2]}"
