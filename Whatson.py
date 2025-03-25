import random
from jellyfin_apiclient_python import JellyfinClient
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import requests
import io
import webbrowser

# Jellyfin setup
client = JellyfinClient()
client.config.app('Jellyfin TV UI', '1.0', 'MomDevice', 'MomDeviceId')
client.config.data['auth.ssl'] = False  # Set to True if using HTTPS
JELLYFIN_URL = 'http://localhost:8096'  # Your server URL

# Connect to server
print("Connecting to server:", JELLYFIN_URL)
client.auth.connect_to_server({'address': JELLYFIN_URL})

# Authenticate and store user ID
print("Attempting login...")
credentials = client.auth.login(JELLYFIN_URL, 'test', 'test')  # Replace with your actual credentials
if not credentials or 'User' not in credentials:
    raise Exception("Failed to authenticate. Check server URL, username, and password.")
USER_ID = credentials['User']['Id']
print("Logged in as user:", USER_ID)

# Fetch all TV shows
def get_shows():
    print("Fetching shows for user:", USER_ID)
    response = client.jellyfin.user_items(params={
        'Recursive': True,
        'IncludeItemTypes': 'Series',
        'Fields': 'Overview,PrimaryImageTag,UserData'
    })
    items = response['Items']
    print(f"Found {len(items)} shows")
    return items

# Download and resize image
def get_image(item, width=200, height=300):  # Adjusted size for vertical layout
    image_tag = item.get('ImageTags', {}).get('Primary', '')
    item_id = item['Id']
    if image_tag:
        url = f"{JELLYFIN_URL}/Items/{item_id}/Images/Primary?tag={image_tag}&maxWidth={width}&maxHeight={height}"
        response = requests.get(url)
        img = Image.open(io.BytesIO(response.content))
        return ImageTk.PhotoImage(img)
    return None

# Get description based on watch status
def get_description(item):
    user_data = item.get('UserData', {})
    if user_data.get('PlayedPercentage', 0) > 0 and user_data.get('PlaybackPositionTicks', 0) > 0:
        item_id = item['Id']
        episode_data = client.jellyfin.get_item(item_id, params={'Fields': 'Overview'})
        if 'UserData' in episode_data and episode_data['UserData']['PlaybackPositionTicks'] > 0:
            return f"Resume {episode_data['Name']} (S{episode_data.get('ParentIndexNumber', '?')}E{episode_data.get('IndexNumber', '?')}): {episode_data.get('Overview', 'No description')}"
    return item.get('Overview', 'No description available')

# Launch show directly (attempt to play video)
def launch_show(item_id):
    # Option 1: Web player URL (best we can do via browser)
    # This opens the Jellyfin web player directly to the item
    play_url = f"{JELLYFIN_URL}/web/index.html#!/video?id={item_id}&serverId={credentials['ServerId']}&play=true"
    webbrowser.open(play_url)
    # Option 2: Direct playback via API (requires external player, see notes below)
    # Not implemented here due to complexity, but explained below

# Main UI class
class JellyfinTVUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Mom’s TV Guide")
        self.root.configure(bg='#f0e6f6')
        self.shows = get_shows()
        self.filtered_shows = self.shows[:]
        self.current_shows = []

        # Style setup
        style = ttk.Style()
        style.configure('TLabel', background='#f0e6f6', font=('Georgia', 12))
        style.configure('Header.TLabel', font=('Georgia', 24, 'bold'), foreground='#6b5b95')

        # Main frame with scrollbar
        main_frame = ttk.Frame(root)
        main_frame.pack(fill='both', expand=True, padx=20, pady=20)

        canvas = tk.Canvas(main_frame, bg='#f0e6f6')
        scrollbar = ttk.Scrollbar(main_frame, orient="vertical", command=canvas.yview)
        self.scrollable_frame = ttk.Frame(canvas)

        self.scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=self.scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        # Header
        ttk.Label(self.scrollable_frame, text="Mom’s Jellyfin TV", style='Header.TLabel').grid(row=0, column=0, columnspan=2, pady=20)

        # Filter input
        filter_frame = ttk.Frame(self.scrollable_frame)
        filter_frame.grid(row=1, column=0, columnspan=2, pady=10, sticky='ew')
        ttk.Label(filter_frame, text="Search Shows:", font=('Georgia', 14)).pack(side=tk.LEFT)
        self.filter_var = tk.StringVar()
        self.filter_entry = ttk.Entry(filter_frame, textvariable=self.filter_var, width=50, font=('Georgia', 12))
        self.filter_entry.pack(side=tk.LEFT, padx=10)
        self.filter_var.trace('w', self.filter_shows)

        # Show rows
        self.show_frames = []
        for i in range(6):
            frame = ttk.Frame(self.scrollable_frame, padding=10)
            frame.grid(row=i+2, column=0, columnspan=2, sticky='ew', pady=10)
            self.show_frames.append(frame)

        # Navigation buttons
        nav_frame = ttk.Frame(self.scrollable_frame)
        nav_frame.grid(row=8, column=0, columnspan=2, pady=20, sticky='ew')
        ttk.Button(nav_frame, text="Previous", command=self.prev_shows).pack(side=tk.LEFT, padx=20)
        ttk.Button(nav_frame, text="Next", command=self.next_shows).pack(side=tk.RIGHT, padx=20)

        # Pack canvas and scrollbar
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        self.load_random_shows()

    def clear_frames(self):
        for frame in self.show_frames:
            for widget in frame.winfo_children():
                widget.destroy()

    def load_random_shows(self):
        self.clear_frames()
        self.current_shows = random.sample(self.filtered_shows, min(6, len(self.filtered_shows)))
        for i, (frame, show) in enumerate(zip(self.show_frames, self.current_shows)):
            # Image (clickable)
            img = get_image(show)
            if img:
                img_label = ttk.Label(frame, image=img)
                img_label.image = img  # Keep reference
                img_label.grid(row=0, column=0, padx=10, pady=5)
                img_label.bind("<Button-1>", lambda e, id=show['Id']: launch_show(id))

            # Title and Description
            ttk.Label(frame, text=show['Name'], font=('Georgia', 16, 'bold'), foreground='#6b5b95').grid(row=0, column=1, sticky='w', padx=10)
            ttk.Label(frame, text=get_description(show), wraplength=600, font=('Georgia', 12)).grid(row=1, column=1, sticky='w', padx=10)

    def filter_shows(self, *args):
        filter_text = self.filter_var.get().lower()
        self.filtered_shows = [
            show for show in self.shows
            if filter_text in show['Name'].lower() or
               filter_text in (show.get('Genres', []) and ','.join(show['Genres']).lower())
        ]
        self.load_random_shows()

    def prev_shows(self):
        self.load_random_shows()

    def next_shows(self):
        self.load_random_shows()

# Run the app
if __name__ == "__main__":
    root = tk.Tk()
    root.geometry("1000x800")  # Adjusted for horizontal layout
    app = JellyfinTVUI(root)
    root.mainloop()