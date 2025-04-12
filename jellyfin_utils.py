from jellyfin_apiclient_python import JellyfinClient
import requests
import io
from PIL import Image, ImageTk
import webbrowser
import random
import subprocess
import os
from screeninfo import get_monitors

# Jellyfin setup
client = JellyfinClient()
client.config.app('Whatson', '1.0', 'MomDevice', 'MomDeviceId')
client.config.data['auth.ssl'] = False
JELLYFIN_URL = 'http://localhost:8096'

print("Connecting to server:", JELLYFIN_URL)
server_info = client.auth.connect_to_server({'address': JELLYFIN_URL})
print("Server info:", server_info)

# Attempt to get server ID from server_info
server_id = None
if 'Id' in server_info:
    server_id = server_info['Id']
else:
    # Fallback: Check credentials for server ID
    creds = client.auth.credentials.get()
    print("Credentials after connect:", creds)
    if 'Servers' in creds and creds['Servers']:
        server_id = creds['Servers'][0].get('Id')
    if not server_id:
        raise Exception("Failed to connect to server. Server ID not found in server info or credentials.")
print("Server ID:", server_id)

print("Attempting login...")
credentials = client.auth.login(JELLYFIN_URL, 'Vicki', 'mom')
if not credentials or 'User' not in credentials or 'AccessToken' not in credentials:
    raise Exception("Failed to authenticate. Check server URL, username, and password.")
USER_ID = credentials['User']['Id']
print("Logged in as user:", USER_ID)
print("Login response:", credentials)

# Set up client configuration for authentication
client.config.data['auth.server'] = JELLYFIN_URL       # Server URL
client.config.data['auth.user-id'] = USER_ID           # User ID
client.config.data['auth.server-id'] = server_id       # Server ID
client.config.data['auth.token'] = credentials['AccessToken']  # Access token from login

print("Client configuration after setup:", client.config.data)
print("Credentials after setup:", client.auth.credentials.get())

# Rest of the file remains unchanged
def get_shows():
    print("Fetching shows for user:", USER_ID)
    response = client.jellyfin.user_items(params={
        'Recursive': True,
        'IncludeItemTypes': 'Series,Movie',
        'Fields': 'Overview,PrimaryImageTag,UserData,People,Images,ImageTags'
    })
    items = response['Items']
    print(f"Found {len(items)} shows and movies")
    for item in items[:3]:
        print(f"Show: {item.get('Name', 'Unknown')}, People: {item.get('People', 'No People data')}")
    return items

def get_image(item, width=462, height=260, image_type='Thumb'):
    item_id = item['Id']
    image_tags = item.get('ImageTags', {}).get(image_type, '')
    if image_tags:
        url = f"{JELLYFIN_URL}/Items/{item_id}/Images/{image_type}?tag={image_tags}&maxWidth={width}&maxHeight={height}"
        try:
            response = requests.get(url)
            response.raise_for_status()
            img = Image.open(io.BytesIO(response.content))
            orig_width, orig_height = img.size
            aspect_ratio = orig_width / orig_height
            new_height = height
            new_width = int(new_height * aspect_ratio)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            return ImageTk.PhotoImage(img)
        except (requests.RequestException, IOError):
            print(f"Failed to load {image_type} image for item {item_id}")
    return ImageTk.PhotoImage(Image.new('RGB', (width, height), color='#000000'))

def get_cast_image(person, width=133, height=140):
    person_id = person.get('Id')
    if person_id and person.get('PrimaryImageTag'):
        cast_img_url = f"{JELLYFIN_URL}/Items/{person_id}/Images/Primary?tag={person['PrimaryImageTag']}&maxWidth={width}&maxHeight={height}"
        print(f"Fetching cast image for person {person_id} (Name: {person.get('Name', 'Unknown')}) from URL: {cast_img_url}")
        try:
            response = requests.get(cast_img_url)
            response.raise_for_status()
            cast_img = Image.open(io.BytesIO(response.content))
            print(f"Successfully loaded cast image for person {person_id}")
            return ImageTk.PhotoImage(cast_img)
        except (requests.RequestException, IOError) as e:
            print(f"Failed to load cast image for person {person_id}: {e}")
    else:
        print(f"No image data for person {person_id} (Name: {person.get('Name', 'Unknown')})")
    return ImageTk.PhotoImage(Image.new('RGB', (width, height), color='#000000'))

def get_second_monitor_index():
    """
    Get the index of the HDMI monitor (HDMI-A-1).
    
    Returns:
        int: The index of the HDMI monitor (0-based), or 0 if not found.
    """
    try:
        monitors = get_monitors()
        print(f"Detected monitors: {len(monitors)}")
        for i, monitor in enumerate(monitors):
            print(f"Monitor {i}: {monitor}")
            if monitor.name == 'HDMI-A-1':
                print(f"Found HDMI monitor (HDMI-A-1) at index {i}")
                return i
        print("HDMI-A-1 monitor not found, using default screen (index 0).")
        return 0
    except Exception as e:
        print(f"Error detecting monitors: {e}")
        return 0

def get_non_default_audio_device():
    """
    Get the identifier of the HDMI audio device for the SAMSUNG TV.
    
    Returns:
        str: The identifier of the HDMI audio device.
    """
    try:
        result = subprocess.run(["mpv", "--audio-device=help"], capture_output=True, text=True, check=True)
        lines = result.stdout.splitlines()
        audio_devices = []
        for line in lines:
            line = line.strip()
            # Look for lines that are actual device names
            if line and (line.startswith("alsa/") or line.startswith("pulse/") or line.startswith("auto")):
                audio_devices.append(line)
        print(f"Detected audio devices: {audio_devices}")
        # Look for the SAMSUNG HDMI audio device
        for device in audio_devices:
            if 'hdmi' in device.lower() and 'SAMSUNG' in device:
                print(f"Found SAMSUNG HDMI audio device: {device}")
                return device
        # Fallback to any HDMI device if SAMSUNG isn't found
        for device in audio_devices:
            if 'hdmi' in device.lower() and device != 'auto':
                print(f"Found generic HDMI audio device: {device}")
                return device
        # Hardcode the SAMSUNG HDMI device as a last resort
        print("No HDMI audio device detected, using hardcoded SAMSUNG HDMI device.")
        return "alsa/hdmi:CARD=HDMI,DEV=1"
    except subprocess.CalledProcessError as e:
        print(f"Error listing audio devices: {e}")
        print("Falling back to hardcoded SAMSUNG HDMI device.")
        return "alsa/hdmi:CARD=HDMI,DEV=1"
    except FileNotFoundError:
        print("MPV not found. Please ensure MPV is installed.")
        return None

def get_media_url(item_id):
    """
    Get the direct media URL for the given item_id from Jellyfin.
    
    Args:
        item_id (str): The ID of the show, movie, or episode.
    
    Returns:
        str: The direct URL to the media file, or None if retrieval fails.
    """
    print(f"Fetching media URL for item {item_id}")
    try:
        # Fetch the item to get its media sources
        item = client.jellyfin.get_item(item_id)
        if 'MediaSources' not in item or not item['MediaSources']:
            print(f"No media sources found for item {item_id}")
            return None
        media_source = item['MediaSources'][0]
        media_source_id = media_source['Id']
        # Get the access token from the client's config
        creds = client.auth.credentials.get()
        print(f"Credentials content: {creds}")
        # Access the AccessToken from the first server in the Servers list
        access_token = None
        if 'Servers' in creds and creds['Servers']:
            access_token = creds['Servers'][0].get('AccessToken')
        if not access_token:
            print("Access token not found in credentials. Attempting to use config token.")
            access_token = client.config.data.get('auth.token')
        if not access_token:
            print("Failed to retrieve access token from credentials or config.")
            return None
        # Construct the direct stream URL
        server_url = client.config.data.get('auth.server', 'http://localhost:8096')
        media_url = f"{server_url}/Videos/{item_id}/stream?MediaSourceId={media_source_id}&api_key={access_token}"
        print(f"Media URL: {media_url}")
        return media_url
    except Exception as e:
        print(f"Error fetching media URL for item {item_id}: {e}")
        return None

def get_next_episode_to_play(series_id):
    """
    Get the next unwatched episode for the series and a list of all remaining episodes' URLs.
    
    Args:
        series_id (str): The ID of the series.
    
    Returns:
        tuple: (next_episode, remaining_episode_urls), where next_episode is a dict of the next episode to play,
               and remaining_episode_urls is a list of URLs for all remaining episodes.
               Returns (None, []) if no episodes are found.
    """
    print(f"Fetching next episode to play for series {series_id}")
    try:
        # Fetch all episodes for the series
        response = client.jellyfin.user_items(params={
            'ParentId': series_id,
            'Recursive': True,
            'IncludeItemTypes': 'Episode',
            'SortBy': 'ParentIndexNumber,IndexNumber',
            'SortOrder': 'Ascending',
            'Fields': 'Overview,ParentIndexNumber,IndexNumber,UserData'
        })
        episodes = response.get('Items', [])
        if not episodes:
            print(f"No episodes found for series {series_id}")
            return None, []
        print(f"Found {len(episodes)} episodes for series {series_id}")

        # Find the last played episode
        last_played_index = -1
        for i, episode in enumerate(episodes):
            ep_user_data = episode.get('UserData', {})
            if ep_user_data.get('Played', False):
                last_played_index = i

        # Determine the next episode to play
        next_episode_index = last_played_index + 1 if last_played_index >= 0 else 0
        if next_episode_index < len(episodes):
            next_episode = episodes[next_episode_index]
        else:
            next_episode = episodes[0]  # Start from the beginning if all episodes are watched
        print(f"Selected episode to play: {next_episode['Name']} (Index: {next_episode['IndexNumber']})")

        # Get URLs for all remaining episodes
        remaining_episodes = episodes[next_episode_index:]
        remaining_episode_urls = []
        for episode in remaining_episodes:
            episode_id = episode['Id']
            media_url = get_media_url(episode_id)
            if media_url:
                remaining_episode_urls.append(media_url)
        print(f"Created playlist with {len(remaining_episode_urls)} remaining episodes")
        return next_episode, remaining_episode_urls
    except Exception as e:
        print(f"Error fetching next episode for series {series_id}: {e}")
        return None, []

def launch_show(item_id):
    """
    Launch the media associated with the given item_id using MPV.
    If the media is a series, play all remaining episodes starting from the next unwatched episode.
    If the media is an episode or movie, play it directly.
    
    Args:
        item_id (str): The ID of the show, movie, or episode.
    """
    print(f"Launching show with ID {item_id}")
    try:
        # Fetch item information to determine its type
        item = client.jellyfin.get_item(item_id)
        item_type = item['Type']
        print(f"Item type: {item_type}")

        # Determine the audio device
        audio_device = get_non_default_audio_device()

        # Build the base MPV command with full-screen and debug options
        mpv_command = ["mpv", "--fs", "--msg-level=all=debug"]
        if audio_device:
            mpv_command.append(f"--audio-device={audio_device}")

        if item_type == 'Series':
            # For a series, get the next episode and remaining episodes
            next_episode, remaining_episode_urls = get_next_episode_to_play(item_id)
            if not next_episode or not remaining_episode_urls:
                print(f"No episodes found to play for series {item_id}")
                return
            # Create a playlist file
            playlist_path = "playlist.txt"
            with open(playlist_path, "w") as f:
                for url in remaining_episode_urls:
                    f.write(f"{url}\n")
            # Play the playlist
            mpv_command.append(f"--playlist={playlist_path}")
            print(f"Launching playlist with command: {mpv_command}")
            subprocess.run(mpv_command, check=True)
            # Clean up the playlist file
            if os.path.exists(playlist_path):
                os.remove(playlist_path)
        else:
            # For episodes or movies, play directly
            media_url = get_media_url(item_id)
            if not media_url:
                print(f"Failed to get media URL for item {item_id}")
                return
            mpv_command.append(media_url)
            print(f"Launching media {item_id} with command: {mpv_command}")
            subprocess.run(mpv_command, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error launching MPV: {e}")
    except FileNotFoundError:
        print("MPV not found. Please ensure MPV is installed on your system.")
    except Exception as e:
        print(f"Error launching show with ID {item_id}: {e}")

def open_jellyfin_ui():
    """Open the Jellyfin web interface in the default browser."""
    try:
        ui_url = f"{JELLYFIN_URL}/web/index.html"
        print(f"Opening Jellyfin UI at {ui_url}")
        webbrowser.open(ui_url)
    except Exception as e:
        print(f"Error opening Jellyfin UI: {e}")

def get_description(item):
    item_id = item['Id']
    item_type = item.get('Type')
    series_name = item.get('Name', 'Unknown Series')
    print(f"Processing {series_name} (ID: {item_id})")

    if item_type == 'Series':
        try:
            resume_data = client.jellyfin.user_items(params={
                'ParentId': item_id,
                'Recursive': True,
                'IncludeItemTypes': 'Episode',
                'SortBy': 'ParentIndexNumber,IndexNumber',
                'SortOrder': 'Ascending',
                'Fields': 'Overview,ParentIndexNumber,IndexNumber,UserData'
            })
            episodes = resume_data.get('Items', [])
            if not episodes:
                print(f"No episodes found for {series_name}")
                return series_name, None, f"{series_name} {item.get('Overview', 'No description available for {series_name}')}"
            print(f"Found {len(episodes)} episodes for {series_name}")
        except Exception as e:
            print(f"Error fetching episodes for {series_name}: {e}")
            return series_name, None, f"{series_name} {item.get('Overview', 'Error fetching episodes for {series_name}')}"

        season_numbers = set(episode.get('ParentIndexNumber', 0) for episode in episodes)
        has_multiple_seasons = len(season_numbers) > 1

        is_unwatched = True
        for episode in episodes:
            ep_user_data = episode.get('UserData', {})
            if ep_user_data.get('PlaybackPositionTicks', 0) > 0 or ep_user_data.get('Played', False):
                is_unwatched = False
                break

        # Check for partially watched episodes
        for episode in episodes:
            ep_user_data = episode.get('UserData', {})
            season_num = episode.get('ParentIndexNumber')
            episode_num = episode.get('IndexNumber')
            ep_name = episode.get('Name', 'Untitled Episode')
            ep_overview = episode.get('Overview', 'No description available')

            if ep_user_data.get('PlaybackPositionTicks', 0) > 0:
                title_parts = []
                if has_multiple_seasons and season_num is not None and episode_num is not None:
                    title_parts.append(f"{series_name.upper()} Episode {season_num}.{episode_num:02d}:")
                elif episode_num is not None:
                    title_parts.append(f"{series_name.upper()} Episode {episode_num}:")
                else:
                    title_parts.append(f"{series_name.upper()} Episode:")
                title_parts.append(ep_name)
                episode_title = " ".join(title_parts)
                if not ep_overview or ep_overview == "No description available":
                    ep_overview = item.get('Overview', 'No description available')
                return series_name, episode_title, ep_overview

        # Find the last played episode
        last_played_index = -1
        for i, episode in enumerate(episodes):
            ep_user_data = episode.get('UserData', {})
            if ep_user_data.get('Played', False):
                last_played_index = i

        if is_unwatched:
            use_series_overview = random.choice([True, False])
            if use_series_overview:
                return series_name, None, f"{series_name.upper()} {item.get('Overview', 'No description available')}"
        
        next_episode_index = last_played_index + 1 if last_played_index >= 0 else 0
        if next_episode_index < len(episodes):
            next_episode = episodes[next_episode_index]
        else:
            next_episode = episodes[0]
        
        season_num = next_episode.get('ParentIndexNumber')
        episode_num = next_episode.get('IndexNumber')
        ep_name = next_episode.get('Name', 'Untitled Episode')
        ep_overview = next_episode.get('Overview', 'No description available')
        if not ep_overview or ep_overview == "No description available":
            ep_overview = item.get('Overview', 'No description available')
        
        title_parts = []
        if has_multiple_seasons and season_num is not None and episode_num is not None:
            title_parts.append(f"{series_name.upper()} Episode {season_num}.{episode_num:02d}:")
        elif episode_num is not None:
            title_parts.append(f"{series_name.upper()} Episode {episode_num}:")
        else:
            title_parts.append(f"{series_name.upper()} Episode:")
        title_parts.append(ep_name)
        episode_title = " ".join(title_parts)
        return series_name, episode_title, ep_overview

    elif item_type == 'Movie':
        user_data = item.get('UserData', {})
        if user_data.get('PlaybackPositionTicks', 0) > 0:
            return item.get('Name', 'Unknown Movie'), f"{series_name.upper()} Resume", item.get('Overview', 'No description available')
        return item.get('Name', 'Unknown Movie'), None, f"{series_name.upper()} {item.get('Overview', 'No description available')}"

    return series_name, None, f"{series_name} {item.get('Overview', 'No description available')}"