import random
from jellyfin_apiclient_python import JellyfinClient
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import requests
import io
import webbrowser
import ttkbootstrap as tb

# Jellyfin setup
client = JellyfinClient()
client.config.app('Whatson', '1.0', 'MomDevice', 'MomDeviceId')
client.config.data['auth.ssl'] = False
JELLYFIN_URL = 'http://localhost:8096'

print("Connecting to server:", JELLYFIN_URL)
client.auth.connect_to_server({'address': JELLYFIN_URL})

print("Attempting login...")
credentials = client.auth.login(JELLYFIN_URL, 'test', 'test')
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

def get_image(item, width=480, height=270, image_type='Thumb'):
    item_id = item['Id']
    image_tags = item.get('ImageTags', {}).get(image_type, '')
    if image_tags:
        url = f"{JELLYFIN_URL}/Items/{item_id}/Images/{image_type}?tag={image_tags}&maxWidth={width}&maxHeight={height}"
        try:
            response = requests.get(url)
            response.raise_for_status()
            img = Image.open(io.BytesIO(response.content))
            # Get the original aspect ratio
            orig_width, orig_height = img.size
            aspect_ratio = orig_width / orig_height
            # Resize to fit the specified height (270) while maintaining aspect ratio
            new_height = height
            new_width = int(new_height * aspect_ratio)
            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            return ImageTk.PhotoImage(img)
        except (requests.RequestException, IOError):
            print(f"Failed to load {image_type} image for item {item_id}")
    return ImageTk.PhotoImage(Image.new('RGB', (width, height), color='#000000'))

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
                return series_name, None, item.get('Overview', f"No episodes found for {series_name}")
        except Exception as e:
            print(f"Error fetching episodes for {series_name}: {e}")
            return series_name, None, item.get('Overview', f"Error fetching episodes for {series_name}")

        # Determine if the series has multiple seasons
        season_numbers = set(episode.get('ParentIndexNumber', 0) for episode in episodes)
        has_multiple_seasons = len(season_numbers) > 1

        # First, check for partially watched episodes
        for episode in episodes:
            ep_user_data = episode.get('UserData', {})
            season_num = episode.get('ParentIndexNumber')
            episode_num = episode.get('IndexNumber')
            ep_name = episode.get('Name', 'Untitled Episode')
            ep_overview = episode.get('Overview', 'No description available')

            print(f"Episode {ep_name} (S{season_num if season_num is not None else '??'}E{episode_num if episode_num is not None else '??'}): {ep_user_data}")

            if ep_user_data.get('PlaybackPositionTicks', 0) > 0:
                # Build the episode title dynamically based on available data
                title_parts = []
                if has_multiple_seasons and season_num is not None:
                    if episode_num is not None:
                        title_parts.append(f"{season_num}.{str(episode_num).zfill(2)}")
                    else:
                        title_parts.append(f"{season_num}")
                elif episode_num is not None:
                    title_parts.append(f"{str(episode_num).zfill(2)}")
                title_parts.append(ep_name)
                episode_title = " ".join(title_parts)
                return series_name, episode_title, ep_overview

        # Find the last played episode
        last_played_index = -1
        for i, episode in enumerate(episodes):
            ep_user_data = episode.get('UserData', {})
            if ep_user_data.get('Played', False):
                last_played_index = i

        # Determine the next episode to show (either after the last played or the first episode)
        next_episode_index = last_played_index + 1 if last_played_index >= 0 else 0
        if next_episode_index < len(episodes):
            next_episode = episodes[next_episode_index]
            season_num = next_episode.get('ParentIndexNumber')
            episode_num = next_episode.get('IndexNumber')
            ep_name = next_episode.get('Name', 'Untitled Episode')
            ep_overview = next_episode.get('Overview', 'No description available')
            # Build the episode title dynamically based on available data
            title_parts = []
            if has_multiple_seasons and season_num is not None:
                if episode_num is not None:
                    title_parts.append(f"{season_num}.{str(episode_num).zfill(2)}")
                else:
                    title_parts.append(f"{season_num}")
            elif episode_num is not None:
                title_parts.append(f"{str(episode_num).zfill(2)}")
            title_parts.append(ep_name)
            episode_title = " ".join(title_parts)
            return series_name, episode_title, ep_overview
        else:
            # If there are no more episodes, loop back to the first episode
            next_episode = episodes[0]
            season_num = next_episode.get('ParentIndexNumber')
            episode_num = next_episode.get('IndexNumber')
            ep_name = next_episode.get('Name', 'Untitled Episode')
            ep_overview = next_episode.get('Overview', 'No description available')
            # Build the episode title dynamically based on available data
            title_parts = []
            if has_multiple_seasons and season_num is not None:
                if episode_num is not None:
                    title_parts.append(f"{season_num}.{str(episode_num).zfill(2)}")
                else:
                    title_parts.append(f"{season_num}")
            elif episode_num is not None:
                title_parts.append(f"{str(episode_num).zfill(2)}")
            title_parts.append(ep_name)
            episode_title = " ".join(title_parts)
            return series_name, episode_title, ep_overview

    elif item_type == 'Movie':
        user_data = item.get('UserData', {})
        if user_data.get('PlaybackPositionTicks', 0) > 0:
            return item.get('Name', 'Unknown Movie'), f"Resume:", item.get('Overview', 'No description available')
        return item.get('Name', 'Unknown Movie'), None, item.get('Overview', 'No description available')

    return series_name, None, item.get('Overview', 'No description available')

def truncate_description(description):
    """Truncate the description to 650 characters if it exceeds the limit."""
    if len(description) > 700:
        return description[:697] + "..."
    return description

def get_font_size(description):
    desc_length = len(description)
    if desc_length > 500:
        return ('Helvetica', 14), True  # Smallest font, reduce title
    elif desc_length > 420:
        return ('Helvetica', 15), True  # Slightly smaller font, reduce title
    elif desc_length > 300:
        return ('Helvetica', 17), False  # Medium font, normal title
    else:
        return ('Helvetica', 20), False  # Largest font, normal title

def launch_show(item_id):
    play_url = f"{JELLYFIN_URL}/web/index.html#!/video?id={item_id}&serverId={credentials['ServerId']}&play=true"
    webbrowser.open(play_url)

def open_jellyfin_ui():
    webbrowser.open(f"{JELLYFIN_URL}/web/index.html")

class WhatsonUI:
    def filter_shows(self, *args):
        filter_text = self.filter_var.get().lower()
        self.filtered_shows = [
            show for show in self.shows
            if filter_text in show['Name'].lower() or
               filter_text in (show.get('Genres', []) and ','.join(show['Genres']).lower())
        ]
        self.load_random_shows()

    def __init__(self, root):
        self.root = root
        self.root.title("Whatson")
        self.root.geometry("1920x900")
        self.root.configure(bg='#121212')

        self.root.update_idletasks()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = (screen_width // 2) - (1920 // 2)
        y = (screen_height // 2) - (900 // 2)
        self.root.geometry(f"1920x900+{x}+{y}")

        self.shows = get_shows()
        self.filtered_shows = self.shows[:]

        top_frame = ttk.Frame(self.root, padding=10)
        top_frame.pack(fill='x', pady=10)

        try:
            logo_img = Image.open("path/to/logo.png")
            logo_img = logo_img.resize((50, 50), Image.Resampling.LANCZOS)
            self.logo = ImageTk.PhotoImage(logo_img)
            ttk.Label(top_frame, image=self.logo).pack(side=tk.LEFT, padx=10)
        except:
            ttk.Label(top_frame, text="[Logo]", font=('Helvetica', 14), foreground='#ffffff').pack(side=tk.LEFT, padx=10)

        ttk.Label(top_frame, text="Whatson", font=('Helvetica', 28, 'bold'), foreground='#ffffff').pack(side=tk.LEFT, padx=10)

        search_frame = ttk.Frame(top_frame)
        search_frame.pack(side=tk.LEFT, padx=20)
        ttk.Label(search_frame, text="Search Shows:", font=('Helvetica', 16), foreground='#ffffff').pack(side=tk.LEFT)
        self.filter_var = tk.StringVar()
        self.filter_entry = ttk.Entry(search_frame, textvariable=self.filter_var, width=50, font=('Helvetica', 14))
        self.filter_entry.pack(side=tk.LEFT, padx=10)
        self.filter_var.trace('w', self.filter_shows)

        ttk.Button(top_frame, text="Open Jellyfin", command=open_jellyfin_ui, style='primary.TButton').pack(side=tk.RIGHT, padx=10)

        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill='both', expand=True)

        self.show_frames = []
        for i in range(5):
            frame = ttk.Frame(main_frame, height=270, padding=5, style="DarkBlue.TFrame")
            frame.pack(fill='x', pady=5)
            frame.pack_propagate(False)
            self.show_frames.append(frame)

        self.load_random_shows()

    def clear_frames(self):
        for frame in self.show_frames:
            for widget in frame.winfo_children():
                widget.destroy()

    def load_random_shows(self):
        self.clear_frames()
        # Filter shows that have both a title (Name) and cast (People)
        valid_shows = [
            show for show in self.filtered_shows
            if show.get('Name') and show.get('Name').strip()  # Non-empty title
            and show.get('People') and len(show.get('People')) > 0  # Non-empty cast list
        ]
        # Select up to 5 shows from the valid ones
        selected_shows = random.sample(valid_shows, min(5, len(valid_shows)))
        self.current_shows = selected_shows

        for frame, show in zip(self.show_frames, self.current_shows):
            channel_logo = ttk.Label(frame, text="[Channel Logo]", width=15, anchor='center', 
                                    foreground='#ffffff', style="DarkBlue.TLabel")
            channel_logo.pack(side=tk.LEFT, padx=2)

            # Thumbnail with aspect ratio preserved, height=270
            img = get_image(show, width=480, height=270, image_type='Thumb')
            img_label = ttk.Label(frame, image=img)
            img_label.image = img
            img_label.pack(side=tk.LEFT)  # Removed padx=4

            description_frame = ttk.Frame(frame, width=772)
            description_frame.pack(side=tk.LEFT, fill='both', expand=True, padx=4)
            description_frame.pack_propagate(False)

            # Get the show title, episode title, and description
            show_title, episode_title, description = get_description(show)
            description = truncate_description(description)
            font, reduce_title = get_font_size(description)

            # Create a frame for the show title (centered)
            title_frame = ttk.Frame(description_frame)
            title_frame.pack(side=tk.TOP, fill='x', pady=(5, 5))

            # Show title (centered)
            title_font = ('Roboto', 20, 'bold') if reduce_title else ('Roboto', 28, 'bold')
            show_title_label = ttk.Label(
                title_frame,
                text=show_title,
                font=title_font,
                foreground='#A8D5E2',
                anchor='center'
            )
            show_title_label.pack(side=tk.TOP, fill='x', expand=True)

            # Create a separate frame for the episode title (movable)
            if episode_title:
                episode_title_frame = ttk.Frame(description_frame)
                episode_title_frame.pack(side=tk.TOP, fill='x')

                episode_title_label = ttk.Label(
                    episode_title_frame,
                    text=episode_title,
                    font=('Helvetica', 16, 'bold'),
                    foreground='#ffffff',
                    anchor='w'
                )
                episode_title_label.pack(side=tk.LEFT)

            # Display the description
            desc_label = ttk.Label(
                description_frame,
                text=description,
                wraplength=1265,
                font=font,
                foreground='#ffffff',
                justify='left',
                anchor='w'
            )
            desc_label.pack(side=tk.TOP, anchor='w', padx=(15, 0), fill='both', expand=True)

            cast_frame = ttk.Frame(frame, width=750)
            cast_frame.pack(side=tk.LEFT, fill='y', padx=2)
            cast_frame.pack_propagate(False)
            cast_container = ttk.Frame(cast_frame)
            cast_container.pack(side=tk.TOP, pady=5)

            people = show.get('People', [])
            for person in people[:5]:
                person_id = person.get('Id')
                if person_id and person.get('PrimaryImageTag'):
                    cast_img_url = f"{JELLYFIN_URL}/Items/{person_id}/Images/Primary?tag={person['PrimaryImageTag']}&maxWidth=128&maxHeight=190"
                    try:
                        response = requests.get(cast_img_url)
                        response.raise_for_status()
                        cast_img = Image.open(io.BytesIO(response.content))
                        cast_photo = ImageTk.PhotoImage(cast_img)
                    except (requests.RequestException, IOError):
                        cast_photo = ImageTk.PhotoImage(Image.new('RGB', (128, 190), color='#000000'))
                else:
                    cast_photo = ImageTk.PhotoImage(Image.new('RGB', (128, 190), color='#000000'))

                cast_member_frame = ttk.Frame(cast_container)
                cast_member_frame.pack(side=tk.LEFT, padx=2)

                cast_label = ttk.Label(cast_member_frame, image=cast_photo)
                cast_label.image = cast_photo
                cast_label.pack(side=tk.TOP, pady=(0, 0))

                name = person.get('Name', 'Unknown')
                parts = name.split()
                if len(parts) > 1:
                    first_line = parts[0]
                    second_line = " ".join(parts[1:])
                else:
                    first_line = name
                    second_line = ""

                if len(first_line) > 10:
                    first_line = first_line[:9] + "."
                if len(second_line) > 10:
                    second_line = second_line[:9] + "."

                formatted_name = f"{first_line}\n{second_line}"

                name_label = ttk.Label(
                    cast_member_frame,
                    text=formatted_name,
                    font=('Monospace', 9),
                    foreground='#ffffff',
                    justify='center',
                    anchor='center',
                    compound='text'
                )
                name_label.pack(side=tk.TOP, pady=(0, 0))

                style = ttk.Style()
                style.configure("Tight.TLabel", font=('Monospace', 9), foreground='#ffffff', anchor='center', justify='center')
                name_label.configure(style="Tight.TLabel")

            poster_frame = ttk.Frame(frame, width=180)
            poster_frame.pack(side=tk.RIGHT, fill='y', padx=4)
            poster_frame.pack_propagate(False)

            poster_container = ttk.Frame(poster_frame)
            poster_container.pack(expand=True)

            poster_img = get_image(show, width=180, height=270, image_type='Primary')
            poster_label = ttk.Label(poster_container, image=poster_img)
            poster_label.image = poster_img
            poster_label.pack()
            poster_label.bind("<Button-1>", lambda e, id=show['Id']: launch_show(id))
if __name__ == "__main__":
    root = tb.Window(themename="cyborg")
    style = ttk.Style()
    style.configure("DarkBlue.TFrame", background="#1a2b4c")
    style.configure("DarkBlue.TLabel", background="#1a2b4c", foreground="#ffffff")
    app = WhatsonUI(root)
    root.mainloop()