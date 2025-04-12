#!/usr/bin/env python3
import random
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import ttkbootstrap as tb
import os
import traceback

from jellyfin_utils import get_shows, get_image, launch_show, open_jellyfin_ui, get_description, get_cast_image
from ui_utils import truncate_description, get_font_size
from generate_content_list import fetch_all_items, load_cached_boxsets, get_collections_for_item, order_content

class WhatsonUI:
    def __init__(self, root):
        try:
            print("Initializing WhatsonUI...")
            self.root = root
            self.root.title("Whatson")

            # Set window dimensions directly
            original_width = 1920
            original_height = 600

            self.root.geometry(f"{original_width}x{original_height}")
            self.root.configure(bg='#121212')

            # Maximize the window on the primary monitor (Linux-compatible method)
            print("Setting window geometry...")
            self.root.attributes('-zoomed', True)
            self.root.update_idletasks()
            screen_width = self.root.winfo_screenwidth()
            screen_height = self.root.winfo_screenheight()
            x = 0
            y = 0
            self.root.geometry(f"+{x}+{y}")

            self.color_scheme = {
                "bg": "#121212",
                "series": "#FFA500",  # Option 3: Orange
                "episode": "#ADFF2F",  # Option 3: Lime Green
                "desc": "#FFFFFF"
            }

            # Load cached BoxSet data
            print("Loading cached BoxSet data...")
            self.cached_boxsets, self.item_to_boxsets = load_cached_boxsets()
            if self.cached_boxsets is None or self.item_to_boxsets is None:
                raise Exception("Failed to load cached BoxSet data. Run generate_content_list.py first.")

            # Fetch and order the content list
            print("Fetching shows...")
            self.shows = fetch_all_items()
            self.filtered_shows = self.shows[:]

            # Assign channels
            self.channel_assignments = {}
            for item in self.shows:
                collections = get_collections_for_item(item['Id'], self.item_to_boxsets)
                self.channel_assignments[item['Id']] = random.choice(collections)  # Randomly select a channel

            # Order the content list (randomized order, max one channel per group of 5)
            self.ordered_shows = order_content(self.shows, self.channel_assignments)

            print("Setting up top frame...")
            top_frame = ttk.Frame(self.root, padding=5)
            top_frame.pack(fill='x', pady=5)

            print("Loading logo image...")
            try:
                logo_img = Image.open("path/to/logo.png")
                logo_img = logo_img.resize((40, 40), Image.Resampling.LANCZOS)
                self.logo = ImageTk.PhotoImage(logo_img)
                ttk.Label(top_frame, image=self.logo).pack(side=tk.LEFT, padx=10)
            except:
                print("Failed to load logo image, using placeholder text.")
                ttk.Label(top_frame, text="[Logo]", font=('Helvetica', 14), foreground='#ffffff').pack(side=tk.LEFT, padx=10)

            ttk.Label(top_frame, text="Whatson", font=('Helvetica', 16, 'bold'), foreground='#ffffff').pack(side=tk.LEFT, padx=10)

            search_frame = ttk.Frame(top_frame)
            search_frame.pack(side=tk.LEFT, padx=20)
            ttk.Label(search_frame, text="Search Shows:", font=('Helvetica', 10), foreground='#ffffff').pack(side=tk.LEFT)
            self.filter_var = tk.StringVar()
            self.filter_entry = ttk.Entry(search_frame, textvariable=self.filter_var, width=50, font=('Helvetica', 8))
            self.filter_entry.pack(side=tk.LEFT, padx=10)
            self.filter_var.trace('w', self.filter_shows)

            # Bind keypress event to focus the search bar
            self.root.bind('<KeyPress>', self.focus_search_bar)

            main_frame = ttk.Frame(self.root, padding=0)
            main_frame.pack(fill='both', expand=True, pady=0)

            self.show_frames = []
            for i in range(5):
                frame = ttk.Frame(main_frame, height=184, padding=0, style="DarkBlue.TFrame")
                frame.pack(fill='x', pady=(0, 5))
                frame.pack_propagate(False)
                self.show_frames.append(frame)

            print("Loading initial shows...")
            self.load_ordered_shows()
            print("WhatsonUI initialization complete.")
        except Exception as e:
            print(f"Error initializing WhatsonUI: {e}")
            traceback.print_exc()
            raise

    def focus_search_bar(self, event):
        # Ignore certain keys (e.g., modifier keys, arrow keys, etc.)
        if event.char and event.char.isprintable():
            # Check if the search bar is already focused
            if self.root.focus_get() != self.filter_entry:
                self.filter_entry.focus_set()
                self.filter_entry.insert(tk.END, event.char)
            # Prevent the event from propagating further
            return "break"

    def filter_shows(self, *args):
        filter_text = self.filter_var.get().lower()
        self.filtered_shows = [
            show for show in self.ordered_shows
            if filter_text in show['Name'].lower() or
               filter_text in (show.get('Genres', []) and ','.join(show['Genres']).lower())
        ]
        self.load_ordered_shows()

    def clear_frames(self):
        for frame in self.show_frames:
            for widget in frame.winfo_children():
                widget.destroy()

    def load_ordered_shows(self):
        try:
            self.clear_frames()

            # Take the first 5 shows from the ordered list, ensuring they have a name
            valid_shows = [
                show for show in self.filtered_shows
                if show.get('Name') and show.get('Name').strip()
            ]
            selected_shows = valid_shows[:5]
            self.current_shows = selected_shows

            scheme = self.color_scheme

            for frame, show in zip(self.show_frames, self.current_shows + [None] * (5 - len(self.current_shows))):
                if show is None:
                    continue  # Skip empty slots

                # Channel image
                channel = self.channel_assignments[show['Id']]
                print(f"Loading channel logo for {show.get('Name', 'Unknown')}: {channel}")
                channel_img = self.get_channel_image(channel)
                channel_logo = ttk.Label(frame, image=channel_img)
                channel_logo.image = channel_img  # Keep reference
                channel_logo.pack(side=tk.LEFT, padx=2)

                img = get_image(show, width=327, height=184, image_type='Thumb')
                img_label = ttk.Label(frame, image=img)
                img_label.image = img
                img_label.pack(side=tk.LEFT, padx=2)
                # Bind launch_show to the thumb banner with debug print
                img_label.bind("<Button-1>", lambda e, id=show['Id']: self.on_thumb_click(id))

                description_frame = ttk.Frame(frame, width=700, style="DarkBlue.TFrame")
                description_frame.pack(side=tk.LEFT, fill='both', expand=True, padx=2)
                description_frame.pack_propagate(False)

                show_title, episode_title, description = get_description(show)
                description = truncate_description(description)

                series_font_size, desc_font_size, reduce_title = get_font_size(description, show_title, episode_title)

                episode_font_family = "Arial"
                episode_font_color = scheme["episode"]
                desc_font_family = "Helvetica"
                desc_font_color = scheme["desc"]

                desc_text = tk.Text(
                    description_frame,
                    wrap='word',
                    foreground='#ffffff',
                    background=scheme["bg"],
                    borderwidth=0,
                    highlightthickness=0,
                    height=10
                )
                desc_text.pack(expand=True, fill='both')

                desc_text.tag_configure("series_name", 
                                        font=(desc_font_family, series_font_size, "underline"),
                                        foreground=scheme["series"],
                                        spacing1=5,
                                        spacing3=0)
                desc_text.tag_configure("spacer", 
                                        font=(desc_font_family, desc_font_size),
                                        foreground=scheme["series"],
                                        spacing1=0,
                                        spacing3=0)
                desc_text.tag_configure("episode_prefix", 
                                        font=(episode_font_family, desc_font_size),
                                        foreground=episode_font_color,
                                        spacing1=0,
                                        spacing3=0)
                desc_text.tag_configure("episode_name", 
                                        font=(episode_font_family, desc_font_size, "italic"),
                                        foreground=episode_font_color,
                                        spacing1=0,
                                        spacing3=0)
                desc_text.tag_configure("description", 
                                        font=(desc_font_family, desc_font_size),
                                        foreground=desc_font_color,
                                        spacing1=0,
                                        spacing3=2)
                desc_text.tag_configure("period", 
                                        font=(episode_font_family, desc_font_size),
                                        foreground="#ADFF2F",
                                        spacing1=0,
                                        spacing3=0)

                # Calculate desc_length for conditional formatting (includes episode title if present)
                desc_length = len(description)
                if episode_title:
                    desc_length += len(episode_title) + 2  # Account for episode title and ": "

                # Handle case where there is an episode title
                if episode_title:
                    # Split episode title into series part and episode part (e.g., "MARE OF EASTTOWN Episode 1: Miss Lady Hawk Herself")
                    parts = episode_title.split(" Episode ", 1)
                    if len(parts) == 2:
                        # Series part (e.g., "MARE OF EASTTOWN") and episode part (e.g., "1: Miss Lady Hawk Herself")
                        series_part = parts[0]
                        episode_part = parts[1]
                        # Further split episode part into episode number and name (e.g., "1" and "Miss Lady Hawk Herself")
                        episode_subparts = episode_part.split(": ", 1)
                        if len(episode_subparts) == 2:
                            episode_prefix = f"Episode {episode_subparts[0]}"  # e.g., "Episode 1"
                            episode_name = episode_subparts[1]  # e.g., "Miss Lady Hawk Herself"
                        else:
                            episode_prefix = f"Episode {episode_part}"  # e.g., "Episode 1"
                            episode_name = ""

                        # Insert series part (e.g., "MARE OF EASTTOWN")
                        desc_text.insert(tk.END, series_part, "series_name")
                        desc_text.insert(tk.END, "     ", "spacer")  # 5 spaces between series and episode

                        if desc_length <= 350:
                            # For shorter descriptions, put episode info on the same line and description on the next line
                            desc_text.insert(tk.END, episode_prefix, "episode_prefix")
                            if episode_name:
                                desc_text.insert(tk.END, ": ", "episode_prefix")
                                desc_text.insert(tk.END, episode_name, "episode_name")
                            desc_text.insert(tk.END, ".", "period")
                            desc_text.insert(tk.END, "\n", "description")
                            # Add extra newline if description (excluding titles) is < 200
                            if len(description) < 300:
                                desc_text.insert(tk.END, "\n", "description")
                            desc_text.insert(tk.END, description, "description")
                        else:
                            # For longer descriptions, keep everything on the same line
                            desc_text.insert(tk.END, episode_prefix, "episode_prefix")
                            if episode_name:
                                desc_text.insert(tk.END, ": ", "episode_prefix")
                                desc_text.insert(tk.END, episode_name, "episode_name")
                            desc_text.insert(tk.END, ".", "period")
                            desc_text.insert(tk.END, " ", "description")
                            desc_text.insert(tk.END, description, "description")
                    else:
                        # Episode title doesn't follow the expected format, treat it as a simple episode title
                        desc_text.insert(tk.END, show_title.upper(), "series_name")
                        desc_text.insert(tk.END, "     ", "spacer")
                        if desc_length <= 350:
                            desc_text.insert(tk.END, episode_title, "episode_prefix")
                            desc_text.insert(tk.END, ".", "period")
                            desc_text.insert(tk.END, "\n", "description")
                            if len(description) < 200:
                                desc_text.insert(tk.END, "\n", "description")
                            desc_text.insert(tk.END, description, "description")
                        else:
                            desc_text.insert(tk.END, episode_title, "episode_prefix")
                            desc_text.insert(tk.END, ".", "period")
                            desc_text.insert(tk.END, " ", "description")
                            desc_text.insert(tk.END, description, "description")
                else:
                    # No episode title, just the series title and description
                    desc_text.insert(tk.END, show_title.upper(), "series_name")
                    desc_text.insert(tk.END, " ", "spacer")
                    desc_part = description
                    if description.startswith(show_title.upper() + " "):
                        desc_part = description[len(show_title.upper()) + 1:]
                    if desc_length <= 350:
                        desc_text.insert(tk.END, "\n", "description")
                        if len(description) < 330:
                            desc_text.insert(tk.END, "\n", "description")
                    else:
                        desc_text.insert(tk.END, " ", "description")
                    desc_text.insert(tk.END, desc_part, "description")

                desc_text.tag_configure("center", justify='left')
                desc_text.tag_add("center", "1.0", "end")
                desc_text.configure(state='disabled')

                cast_frame = ttk.Frame(frame, width=500, style="DarkBlue.TFrame")
                cast_frame.pack(side=tk.LEFT, fill='y', padx=0)
                cast_frame.pack_propagate(False)
                print(f"Packed cast_frame for {show.get('Name', 'Unknown')} with width=500")
                cast_container = ttk.Frame(cast_frame)
                cast_container.pack(side=tk.TOP, pady=0)
                print(f"Packed cast_container for {show.get('Name', 'Unknown')}")

                people = show.get('People', [])
                for i, person in enumerate(people[:5]):
                    cast_photo = get_cast_image(person, width=90, height=140)
                    print(f"Loaded cast photo for {person.get('Name', 'Unknown')} (slot {i+1}) in {show.get('Name', 'Unknown')}")
                    cast_member_frame = ttk.Frame(cast_container,width=135)
                    cast_member_frame.pack(side=tk.LEFT, padx=2)
                    print(f"Packed cast_member_frame for slot {i+1} in {show.get('Name', 'Unknown')}")
                    cast_label = ttk.Label(cast_member_frame, image=cast_photo, style="Cast.TLabel")
                    cast_label.image = cast_photo
                    cast_label.pack(side=tk.TOP, pady=(0, 0))
                    print(f"Set cast photo for {person.get('Name', 'Unknown')} on ttk.Label in slot {i+1}")
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
                        foreground=scheme["desc"],
                        justify='center',
                        anchor='center',
                        compound='text',
                        style="Cast.TLabel"
                    )
                    name_label.pack(side=tk.TOP, pady=(0, 0))
                    print(f"Set name label for {person.get('Name', 'Unknown')} in slot {i+1}")
                # Add placeholders for remaining slots
                for i in range(len(people), 5):
                    cast_photo = ImageTk.PhotoImage(Image.new('RGB', (90, 140), color='#000000'))
                    print(f"Using blank placeholder for cast slot {i+1} in {show.get('Name', 'Unknown')}")
                    cast_member_frame = ttk.Frame(cast_container)
                    cast_member_frame.pack(side=tk.LEFT, padx=2)
                    print(f"Packed cast_member_frame for slot {i+1} (placeholder) in {show.get('Name', 'Unknown')}")
                    cast_label = ttk.Label(cast_member_frame, image=cast_photo, style="Cast.TLabel")
                    cast_label.image = cast_photo
                    cast_label.pack(side=tk.TOP, pady=(0, 0))
                    print(f"Set blank placeholder on ttk.Label for slot {i+1}")
                    name_label = ttk.Label(
                        cast_member_frame,
                        text="\n",
                        font=('Monospace', 9),
                        foreground=scheme["desc"],
                        justify='center',
                        anchor='center',
                        compound='text',
                        style="Cast.TLabel"
                    )
                    name_label.pack(side=tk.TOP, pady=(0, 0))
                    print(f"Set blank name label for slot {i+1}")

                poster_frame = ttk.Frame(frame, width=129, style="DarkBlue.TFrame")
                poster_frame.pack(side=tk.RIGHT, fill='y', padx=2)
                poster_frame.pack_propagate(False)
                poster_container = ttk.Frame(poster_frame)
                poster_container.pack(expand=True)
                poster_img = get_image(show, width=129, height=184, image_type='Primary')
                poster_label = ttk.Label(poster_container, image=poster_img)
                poster_label.image = poster_img
                poster_label.pack()
        except Exception as e:
            print(f"Error in load_ordered_shows: {e}")
            traceback.print_exc()
            raise

    def on_thumb_click(self, item_id):
        """Handle thumb banner click event."""
        print(f"Thumb banner clicked for item ID: {item_id}")
        launch_show(item_id)

    def get_channel_image(self, channel):
        """Load channel image or fallback to placeholder."""
        img_path = os.path.join("Channels", f"{channel}.png")
        width, height = 141, 184  # Based on your existing channel logo dimensions
        print(f"Attempting to load channel image: {img_path}")
        if os.path.exists(img_path):
            print(f"Channel image found: {img_path}")
            return ImageTk.PhotoImage(Image.open(img_path).resize((width, height), Image.Resampling.LANCZOS))
        print(f"Channel image not found: {img_path}, using blank placeholder")
        return ImageTk.PhotoImage(Image.new('RGB', (width, height), color='#000000'))

if __name__ == "__main__":
    try:
        print("Starting Whatson application...")
        root = tb.Window(themename="cyborg")
        style = ttk.Style()
        style.configure("DarkBlue.TFrame", background="#0A1A2F")
        style.configure("DarkBlue.TLabel", background="#0A1A2F", foreground="#ffffff")
        # New style for cast labels with very dark grey background
        style.configure("Cast.TLabel", background="#333333", foreground="#ffffff")
        app = WhatsonUI(root)
        print("Starting Tkinter main loop...")
        root.mainloop()
        print("Application closed.")
    except Exception as e:
        print(f"Error starting application: {e}")
        traceback.print_exc()