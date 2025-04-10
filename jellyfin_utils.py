# jellyfin_utils.py
from jellyfin_apiclient_python import JellyfinClient
import requests
import io
from PIL import Image, ImageTk
import webbrowser
import random

# Jellyfin setup
client = JellyfinClient()
client.config.app('Whatson', '1.0', 'MomDevice', 'MomDeviceId')
client.config.data['auth.ssl'] = False
JELLYFIN_URL = 'http://localhost:8096'

print("Connecting to server:", JELLYFIN_URL)
client.auth.connect_to_server({'address': JELLYFIN_URL})

print("Attempting login...")
credentials = client.auth.login(JELLYFIN_URL, 'Vicki', 'mom')
if not credentials or 'User' not in credentials:
    raise Exception("Failed to authenticate. Check server URL, username, and password.")
USER_ID = credentials['User']['Id']
print("Logged in as user:", USER_ID)

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

def get_cast_image(person, width=128, height=190):
    person_id = person.get('Id')
    if person_id and person.get('PrimaryImageTag'):
        cast_img_url = f"{JELLYFIN_URL}/Items/{person_id}/Images/Primary?tag={person['PrimaryImageTag']}&maxWidth={width}&maxHeight={height}"
        try:
            response = requests.get(cast_img_url)
            response.raise_for_status()
            cast_img = Image.open(io.BytesIO(response.content))
            return ImageTk.PhotoImage(cast_img)
        except (requests.RequestException, IOError):
            print(f"Failed to load cast image for person {person_id}")
    return ImageTk.PhotoImage(Image.new('RGB', (width, height), color='#000000'))

# Existing imports and code remain unchanged until the end...

def launch_show(item_id):
    """Launch a show or movie by its Jellyfin item ID."""
    try:
        # Construct the URL to play the item directly in the Jellyfin web player
        play_url = f"{JELLYFIN_URL}/web/index.html#!/details?id={item_id}&userId={USER_ID}"
        print(f"Launching show with ID {item_id} at {play_url}")
        webbrowser.open(play_url)
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

# Existing code continues...

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