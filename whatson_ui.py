#!/usr/bin/env python3
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import ttkbootstrap as tb
import os
import subprocess
import random
import time
import threading
import webbrowser  # Added for opening the browser
from jellyfin_apiclient_python import JellyfinClient

from jellyfin_utils import get_image, launch_show, get_description, get_cast_image
from ui_utils import truncate_description, get_font_size

class WhatsonUI:
    def __init__(self, root, color_scheme, scroll_up_callback, scroll_down_callback, filter_callback, set_search_mode_callback):
        self.root = root
        self.color_scheme = color_scheme
        self.scroll_up_callback = scroll_up_callback
        self.scroll_down_callback = scroll_down_callback
        self.filter_callback = filter_callback
        self.set_search_mode_callback = set_search_mode_callback  # Store the callback

        self.root.title("Whatson")
        original_width = 1920
        original_height = 600
        self.root.geometry(f"{original_width}x{original_height}")
        self.root.configure(bg='#121212')

        self.root.attributes('-zoomed', True)
        self.root.update_idletasks()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = 0
        y = 0
        self.root.geometry(f"+{x}+{y}")

        self.top_frame = ttk.Frame(self.root, padding=5)
        self.top_frame.pack(fill='x', pady=5)

        try:
            logo_img = Image.open("path/to/logo.png")
            logo_img = logo_img.resize((40, 40), Image.Resampling.LANCZOS)
            self.logo = ImageTk.PhotoImage(logo_img)
            ttk.Label(self.top_frame, image=self.logo).pack(side=tk.LEFT, padx=10)
        except:
            ttk.Label(self.top_frame, text="[Logo]", font=('Helvetica', 14), foreground='#ffffff').pack(side=tk.LEFT, padx=10)

        ttk.Label(self.top_frame, text="Whatson", font=('Helvetica', 16, 'bold'), foreground='#ffffff').pack(side=tk.LEFT, padx=10)

        self.search_frame = ttk.Frame(self.top_frame)
        self.search_frame.pack(side=tk.LEFT, padx=20)
        ttk.Label(self.search_frame, text="Search Shows:", font=('Helvetica', 10), foreground='#ffffff').pack(side=tk.LEFT)
        self.filter_var = tk.StringVar()
        self.filter_entry = ttk.Entry(
            self.search_frame,
            textvariable=self.filter_var,
            width=50,
            font=('Helvetica', 12),
            style="Large.TEntry"
        )
        self.filter_entry.pack(side=tk.LEFT, padx=(10, 2))
        self.filter_var.trace('w', self.filter_shows)

        # Add a custom clear button
        clear_button = ttk.Button(
            self.search_frame,
            text="✕",
            command=self.clear_search,
            width=2,
            style="secondary.TButton"
        )
        clear_button.pack(side=tk.LEFT, padx=(0, 10))

        arrow_frame = ttk.Frame(self.top_frame)
        arrow_frame.pack(side=tk.LEFT, padx=5)

        up_button = ttk.Button(
            arrow_frame,
            text="▲",
            command=self.scroll_up,
            width=2,
            style="Arrow.TButton"
        )
        up_button.pack(side=tk.LEFT, padx=2)

        down_button = ttk.Button(
            arrow_frame,
            text="▼",
            command=self.scroll_down,
            width=2,
            style="Arrow.TButton"
        )
        down_button.pack(side=tk.LEFT, padx=2)

        stream_button = ttk.Button(
            self.top_frame,
            text="KIRO 7 Stream",
            command=self.launch_kuro7_stream,
            style="Arrow.TButton"
        )
        stream_button.pack(side=tk.RIGHT, padx=10)

        self.root.bind('<KeyPress>', self.focus_search_bar)
        self.root.bind('<Up>', self.scroll_up)
        self.root.bind('<Down>', self.scroll_down)

        main_frame = ttk.Frame(self.root, padding=0)
        main_frame.pack(fill='both', expand=True, pady=0)

        self.show_frames = []
        self.desc_widgets = {}
        self.selected_episodes = {}
        self.show_ids = {}
        for i in range(5):
            frame = ttk.Frame(main_frame, height=184, padding=0, style="DarkBlue.TFrame")
            frame.pack(fill='x', pady=(0, 5))
            frame.pack_propagate(False)
            self.show_frames.append(frame)
            self.desc_widgets[i] = None

        self.client = JellyfinClient()
        self.client.config.app('Whatson', '1.0', 'MomDevice', 'MomDeviceId')
        self.client.config.data['auth.ssl'] = False
        JELLYFIN_URL = 'http://localhost:8096'
        server_info = self.client.auth.connect_to_server({'address': JELLYFIN_URL})

        server_id = None
        if 'Id' in server_info:
            server_id = server_info['Id']
        else:
            creds = self.client.auth.credentials.get()
            if 'Servers' in creds and creds['Servers']:
                server_id = creds['Servers'][0].get('Id')
            if not server_id:
                raise Exception("Failed to connect to server. Server ID not found in server info or credentials.")
        self.server_id = server_id  # Store server_id for use in web player URL

        credentials = self.client.auth.login(JELLYFIN_URL, 'Vicki', 'mom')
        if not credentials or 'User' not in credentials or 'AccessToken' not in credentials:
            raise Exception("Failed to authenticate. Check server URL, username, and password.")
        self.user_id = credentials['User']['Id']

        self.client.config.data['auth.server'] = JELLYFIN_URL
        self.client.config.data['auth.user-id'] = self.user_id
        self.client.config.data['auth.server-id'] = server_id
        self.client.config.data['auth.token'] = credentials['AccessToken']

        self.current_menu = None
        self.menu_x = 0
        self.menu_y = 0
        self.menu_width = 0
        self.menu_height = 0
        self.loading_label = None  # Initialize the loading label as None
        self.flashing = False  # Flag to control the flashing loop

    def focus_search_bar(self, event):
        if event.char and event.char.isprintable():
            if self.root.focus_get() != self.filter_entry:
                self.filter_entry.focus_set()
                self.filter_entry.insert(tk.END, event.char)
            return "break"

    def clear_search(self):
        """Clear the search bar and trigger a re-filter."""
        self.filter_var.set("")
        self.filter_shows()

    def filter_shows(self, *args):
        self.filter_callback(*args)

    def scroll_up(self, event=None):
        self.scroll_up_callback(event)

    def scroll_down(self, event=None):
        self.scroll_down_callback(event)

    def clear_frames(self):
        for frame in self.show_frames:
            for widget in frame.winfo_children():
                widget.destroy()
        self.show_ids.clear()
        for i in range(5):
            self.desc_widgets[i] = None

    def show_loading_indicator(self):
        """Hide the search bar and show a flashing 'LOADING' label in the center of the top frame."""
        # Hide the search frame
        if self.search_frame.winfo_exists():
            self.search_frame.pack_forget()

        # Create the "LOADING" label if it doesn't exist
        if self.loading_label is None or not self.loading_label.winfo_exists():
            self.loading_label = ttk.Label(
                self.top_frame,
                text="LOADING",
                font=('Helvetica', 21, 'bold'),  # Updated font size to 21
                foreground='#FFFF00'  # Yellow
            )
            self.loading_label.pack(side=tk.TOP, expand=True)

        # Start flashing the label
        self.flashing = True
        def flash():
            if not self.flashing or not self.loading_label.winfo_exists():
                return
            # Toggle visibility
            if self.loading_label.winfo_viewable():
                self.loading_label.pack_forget()
            else:
                self.loading_label.pack(side=tk.TOP, expand=True)
            # Schedule the next toggle
            self.root.after(500, flash)

        flash()

    def hide_loading_indicator(self):
        """Stop flashing and hide the loading label."""
        self.flashing = False
        if self.loading_label and self.loading_label.winfo_exists():
            self.loading_label.pack_forget()

    def launch_kuro7_stream(self):
        """Launch the KIRO 7 video stream, clear all rows, show loading indicator, and close the UI after a delay."""
        # Show the loading indicator
        self.show_loading_indicator()

        # Clear content of all frames immediately
        def update_ui():
            for frame in self.show_frames:
                if frame.winfo_exists():
                    self.clear_frame_content(frame)

        self.root.after(0, update_ui)  # Update UI immediately (delay = 0)

        # Launch the stream in a separate thread
        def start_mpv():
            stream_url = "https://amg00327-coxmediagroup-kironow-ono-zkqw3.amagi.tv/playlist/amg00327-coxmediagroup-kironow-ono/390ed178-1753-11f0-b595-06caa58e52b6/89/640x360_1057680/index.m3u8"
            try:
                audio_device = self.get_non_default_audio_device()
                mpv_command = ["mpv", "--fs", "--msg-level=all=info"]
                if audio_device:
                    mpv_command.append(f"--audio-device={audio_device}")
                mpv_command.append(stream_url)
                subprocess.run(mpv_command, check=True)
            except subprocess.CalledProcessError as e:
                print(f"Error launching MPV for KIRO 7 stream: {e}")
            except FileNotFoundError:
                print("MPV not found. Please ensure MPV is installed on your system.")
            except Exception as e:
                print(f"Error launching KIRO 7 stream: {e}")

        # Start MPV in a separate thread
        threading.Thread(target=start_mpv, daemon=True).start()

        # After 4 seconds, close the main UI (changed from 5s to 4s)
        self.root.after(4000, self.close_ui)

    def get_non_default_audio_device(self):
        try:
            result = subprocess.run(["mpv", "--audio-device=help"], capture_output=True, text=True, check=True)
            lines = result.stdout.splitlines()
            audio_devices = []
            for line in lines:
                line = line.strip()
                if line and (line.startswith("alsa/") or line.startswith("pulse/") or line.startswith("auto")):
                    audio_devices.append(line)
            for device in audio_devices:
                if 'hdmi' in device.lower() and 'SAMSUNG' in device:
                    return device
            for device in audio_devices:
                if 'hdmi' in device.lower() and device != 'auto':
                    return device
            return "alsa/hdmi:CARD=HDMI,DEV=1"
        except subprocess.CalledProcessError as e:
            print(f"Error listing audio devices: {e}")
            return "alsa/hdmi:CARD=HDMI,DEV=1"
        except FileNotFoundError:
            print("MPV not found. Please ensure MPV is installed.")
            return None

    def fetch_episodes(self, show_id):
        """Fetch all episodes for the given show, grouped by season."""
        try:
            response = self.client.jellyfin.user_items(params={
                'ParentId': show_id,
                'Recursive': True,
                'IncludeItemTypes': 'Episode',
                'SortBy': 'ParentIndexNumber,IndexNumber',
                'SortOrder': 'Ascending',
                'Fields': 'Overview,ParentIndexNumber,IndexNumber,UserData'
            })
            episodes = response.get('Items', [])
            if not episodes:
                return None, None

            # Group episodes by season
            seasons = {}
            for episode in episodes:
                season_num = episode.get('ParentIndexNumber', 0)
                if season_num not in seasons:
                    seasons[season_num] = []
                seasons[season_num].append(episode)

            return seasons, episodes
        except Exception as e:
            print(f"Error fetching episodes for show ID {show_id}: {e}")
            return None, None

    def dismiss_menu(self, event):
        """Dismiss the current context menu if a click occurs outside it."""
        if not self.current_menu:
            return

        # Check if the click is outside the menu bounds
        click_x = event.x_root
        click_y = event.y_root
        if (click_x < self.menu_x or click_x > self.menu_x + self.menu_width or
            click_y < self.menu_y or click_y > self.menu_y + self.menu_height):
            self.current_menu.unpost()
            self.current_menu = None
            self.menu_x = 0
            self.menu_y = 0
            self.menu_width = 0
            self.menu_height = 0

    def open_episode_selector(self, show_id, frame_index, event):
        """Open a context menu to select a season and episode for the given show."""
        # Fetch the show details to check its type
        try:
            show = self.client.jellyfin.get_item(show_id)
            item_type = show.get('Type', '')
            if item_type == "Movie":
                return  # Skip opening the menu for movies
        except Exception as e:
            print(f"Error fetching show details for show ID {show_id}: {e}")
            return

        seasons, episodes = self.fetch_episodes(show_id)
        if not seasons or not episodes:
            return

        # If a menu is already open, dismiss it
        if self.current_menu:
            self.current_menu.unpost()
            self.current_menu = None

        # Create the main context menu with a larger font
        menu = tk.Menu(self.root, tearoff=0, bg='#0A1A2F', fg='#ffffff', activebackground='#555555', activeforeground='#ffffff', font=('Helvetica', 24))
        self.current_menu = menu

        # Store the menu position and size (approximate for now, Tkinter doesn't provide direct access to menu geometry)
        self.menu_x = event.x_root
        self.menu_y = event.y_root
        self.menu_width = 300  # Approximate width (can adjust based on font size and content)
        self.menu_height = 400  # Approximate height

        # If there's only one season, skip the season level and show episodes directly
        if len(seasons) == 1:
            season_num = list(seasons.keys())[0]
            for episode in seasons[season_num]:
                episode_num = episode.get('IndexNumber', 'Unknown')
                try:
                    episode_num = int(episode_num)
                except (ValueError, TypeError):
                    episode_num = 0
                episode_name = episode.get('Name', 'Untitled Episode')
                episode_id = episode['Id']
                episode_label = f"E{episode_num}: {episode_name}"
                menu.add_command(label=episode_label, command=lambda eid=episode_id: self.select_episode(eid, show_id))
        else:
            # Add seasons to the menu
            for season_num in sorted(seasons.keys()):
                season_label = f"Season {season_num}" if season_num != 0 else "Specials"
                submenu = tk.Menu(menu, tearoff=0, bg='#0A1A2F', fg='#ffffff', activebackground='#555555', activeforeground='#ffffff', font=('Helvetica', 24))
                menu.add_cascade(label=season_label, menu=submenu)

                # Add episodes to the submenu
                for episode in seasons[season_num]:
                    episode_num = episode.get('IndexNumber', 'Unknown')
                    try:
                        episode_num = int(episode_num)
                    except (ValueError, TypeError):
                        episode_num = 0
                    episode_name = episode.get('Name', 'Untitled Episode')
                    episode_id = episode['Id']
                    episode_label = f"E{episode_num}: {episode_name}"
                    submenu.add_command(label=episode_label, command=lambda eid=episode_id: self.select_episode(eid, show_id))

        # Display the menu at the click position
        try:
            menu.tk_popup(event.x_root, event.y_root)
            # Bind the dismiss event after a short delay to avoid immediate dismissal
            self.root.after(100, lambda: self.root.bind('<Button-1>', self.dismiss_menu))
        finally:
            menu.grab_release()

    def select_episode(self, episode_id, show_id):
        """Handle episode selection from the context menu and update the description."""
        self.selected_episodes[show_id] = episode_id

        # Find the frame index for this show
        frame_index = None
        for idx, sid in self.show_ids.items():
            if sid == show_id:
                frame_index = idx
                break

        if frame_index is None:
            print(f"Could not find frame index for show ID {show_id}")
            return

        # Fetch the episode details and update the description
        try:
            episode = self.client.jellyfin.get_item(episode_id)
            season_num = episode.get('ParentIndexNumber', 0)
            episode_num = episode.get('IndexNumber', 'Unknown')
            try:
                episode_num = int(episode_num)
            except (ValueError, TypeError):
                episode_num = 0
            episode_name = episode.get('Name', 'Untitled Episode')
            episode_overview = episode.get('Overview', 'No description available')
            series_name = episode.get('SeriesName', 'Unknown Series')

            desc_text = self.desc_widgets[frame_index]
            if desc_text:
                desc_text.configure(state='normal')
                desc_text.delete("1.0", tk.END)
                title_parts = []
                if season_num is not None and episode_num is not None:
                    title_parts.append(f"{series_name.upper()} Episode {season_num}.{episode_num:02d}:")
                else:
                    title_parts.append(f"{series_name.upper()} Episode:")
                title_parts.append(episode_name)
                episode_title = " ".join(title_parts)
                description = episode_overview

                # Recalculate font size and spacing based on the new description
                description = truncate_description(description)
                series_font_size, desc_font_size, reduce_title = get_font_size(description, series_name, episode_title)

                # Update the tags with the new font sizes and spacing
                desc_text.tag_configure("series_name",
                                        font=('Helvetica', series_font_size, "underline"),
                                        foreground=self.color_scheme["series"],
                                        spacing1=5,
                                        spacing3=0)
                desc_text.tag_configure("spacer",
                                        font=('Helvetica', desc_font_size),
                                        foreground=self.color_scheme["series"],
                                        spacing1=0,
                                        spacing3=0)
                desc_text.tag_configure("episode_prefix",
                                        font=('Arial', desc_font_size),
                                        foreground=self.color_scheme["episode"],
                                        spacing1=0,
                                        spacing3=0)
                desc_text.tag_configure("episode_name",
                                        font=('Arial', desc_font_size, "italic"),
                                        foreground=self.color_scheme["episode"],
                                        spacing1=0,
                                        spacing3=0)
                desc_text.tag_configure("description",
                                        font=('Helvetica', desc_font_size),
                                        foreground=self.color_scheme["desc"],
                                        spacing1=0,
                                        spacing3=2)
                desc_text.tag_configure("period",
                                        font=('Arial', desc_font_size),
                                        foreground="#ADFF2F",
                                        spacing1=0,
                                        spacing3=0)

                desc_text.insert(tk.END, series_name.upper(), "series_name")
                desc_text.insert(tk.END, "     ", "spacer")
                desc_text.insert(tk.END, f"Episode {season_num}.{episode_num:02d}: {episode_name}", "episode_prefix")
                desc_text.insert(tk.END, ".", "period")
                desc_text.insert(tk.END, "\n", "description")
                desc_text.insert(tk.END, description, "description")
                desc_text.tag_configure("center", justify='left')
                desc_text.tag_add("center", "1.0", "end")
                desc_text.configure(state='disabled')
                desc_text.update_idletasks()
        except Exception as e:
            print(f"Error fetching episode details for episode ID {episode_id}: {e}")

        self.current_menu = None
        self.menu_x = 0
        self.menu_y = 0
        self.menu_width = 0
        self.menu_height = 0

    def load_ordered_shows(self, current_shows, channel_assignments):
        try:
            self.clear_frames()

            scheme = self.color_scheme

            for frame_index, (frame, show) in enumerate(zip(self.show_frames, current_shows + [None] * (5 - len(current_shows)))):
                if show is None:
                    continue

                show_id = show['Id']
                self.show_ids[frame_index] = show_id

                channel = channel_assignments[show_id]
                channel_img = self.get_channel_image(channel)
                channel_logo = ttk.Label(frame, image=channel_img)
                channel_logo.image = channel_img
                channel_logo.pack(side=tk.LEFT, padx=2)
                # Add click event to filter by channel
                channel_logo.bind("<Button-1>", lambda e, ch=channel: self.set_search_mode_callback("channel", ch))

                img = get_image(show, width=327, height=184, image_type='Thumb')
                img_label = ttk.Label(frame, image=img)
                img_label.image = img
                img_label.pack(side=tk.LEFT, padx=2)
                img_label.bind("<Button-1>", lambda e, id=show_id: self.on_thumb_click(id))

                description_frame = ttk.Frame(frame, width=700, style="DarkBlue.TFrame")
                description_frame.pack(side=tk.LEFT, fill='both', expand=True, padx=2)
                description_frame.pack_propagate(False)

                series_name = show.get('Name', 'Unknown Series')
                series_overview = show.get('Overview', 'No description available')

                # Check if an episode has been manually selected
                selected_episode_id = self.selected_episodes.get(show_id)
                if selected_episode_id:
                    # Always show the selected episode's description
                    try:
                        episode = self.client.jellyfin.get_item(selected_episode_id)
                        season_num = episode.get('ParentIndexNumber', 0)
                        episode_num = episode.get('IndexNumber', 'Unknown')
                        try:
                            episode_num = int(episode_num)
                        except (ValueError, TypeError):
                            episode_num = 0
                        episode_name = episode.get('Name', 'Untitled Episode')
                        episode_overview = episode.get('Overview', 'No description available')

                        title_parts = []
                        if season_num is not None and episode_num is not None:
                            title_parts.append(f"{series_name.upper()} Episode {season_num}.{episode_num:02d}:")
                        else:
                            title_parts.append(f"{series_name.upper()} Episode:")
                        title_parts.append(episode_name)
                        episode_title = " ".join(title_parts)
                        description = episode_overview
                    except Exception as e:
                        print(f"Error fetching selected episode details for episode ID {selected_episode_id}: {e}")
                        episode_title = None
                        description = series_overview
                else:
                    # Fetch episodes to determine watched status and first episode
                    seasons, episodes = self.fetch_episodes(show_id)
                    if not episodes:
                        episode_title = None
                        description = series_overview
                    else:
                        # Check if the show is unwatched or fully watched
                        is_unwatched = True
                        all_watched = True
                        for episode in episodes:
                            ep_user_data = episode.get('UserData', {})
                            if ep_user_data.get('PlaybackPositionTicks', 0) > 0 or ep_user_data.get('Played', False):
                                is_unwatched = False
                            if not ep_user_data.get('Played', False):
                                all_watched = False

                        if all_watched:
                            # If all episodes are watched, always show the series overview
                            episode_title = None
                            description = series_overview
                        elif is_unwatched:
                            # If the show is unwatched, 50% chance to show series overview or first episode
                            use_series_overview = random.choice([True, False])
                            if use_series_overview:
                                episode_title = None
                                description = series_overview
                            else:
                                first_episode = episodes[0]
                                season_num = first_episode.get('ParentIndexNumber', 0)
                                episode_num = first_episode.get('IndexNumber', 'Unknown')
                                try:
                                    episode_num = int(episode_num)
                                except (ValueError, TypeError):
                                    episode_num = 0
                                ep_name = first_episode.get('Name', 'Untitled Episode')
                                ep_overview = first_episode.get('Overview', 'No description available')

                                title_parts = []
                                if season_num is not None and episode_num is not None:
                                    title_parts.append(f"{series_name.upper()} Episode {season_num}.{episode_num:02d}:")
                                else:
                                    title_parts.append(f"{series_name.upper()} Episode:")
                                title_parts.append(ep_name)
                                episode_title = " ".join(title_parts)
                                description = ep_overview
                        else:
                            # Default to get_description (shows next unwatched episode)
                            _, episode_title, description = get_description(show)

                description = truncate_description(description)

                series_font_size, desc_font_size, reduce_title = get_font_size(description, series_name, episode_title)

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
                self.desc_widgets[frame_index] = desc_text

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

                desc_text.tag_bind("series_name", "<Button-1>",
                                   lambda e, sid=show_id, fi=frame_index: self.open_episode_selector(sid, fi, e))

                desc_length = len(description)
                if episode_title:
                    desc_length += len(episode_title) + 2

                if episode_title:
                    parts = episode_title.split(" Episode ", 1)
                    if len(parts) == 2:
                        series_part = parts[0]
                        episode_part = parts[1]
                        episode_subparts = episode_part.split(": ", 1)
                        if len(episode_subparts) == 2:
                            episode_prefix = f"Episode {episode_subparts[0]}"
                            episode_name = episode_subparts[1]
                        else:
                            episode_prefix = f"Episode {episode_part}"
                            episode_name = ""

                        desc_text.insert(tk.END, series_part, "series_name")
                        desc_text.insert(tk.END, "     ", "spacer")

                        if desc_length <= 350:
                            desc_text.insert(tk.END, episode_prefix, "episode_prefix")
                            if episode_name:
                                desc_text.insert(tk.END, ": ", "episode_prefix")
                                desc_text.insert(tk.END, episode_name, "episode_name")
                            desc_text.insert(tk.END, ".", "period")
                            desc_text.insert(tk.END, "\n", "description")
                            if len(description) < 300:
                                desc_text.insert(tk.END, "\n", "description")
                            desc_text.insert(tk.END, description, "description")
                        else:
                            desc_text.insert(tk.END, episode_prefix, "episode_prefix")
                            if episode_name:
                                desc_text.insert(tk.END, ": ", "episode_prefix")
                                desc_text.insert(tk.END, episode_name, "episode_name")
                            desc_text.insert(tk.END, ".", "period")
                            desc_text.insert(tk.END, " ", "description")
                            desc_text.insert(tk.END, description, "description")
                    else:
                        desc_text.insert(tk.END, series_name.upper(), "series_name")
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
                    desc_text.insert(tk.END, series_name.upper(), "series_name")
                    desc_text.insert(tk.END, " ", "spacer")
                    desc_part = description
                    if description.startswith(series_name.upper() + " "):
                        desc_part = description[len(series_name.upper()) + 1:]
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

                cast_frame = ttk.Frame(frame, width=500, style="DarkBlue.TFrame", padding=0)
                cast_frame.pack(side=tk.LEFT, fill='y', padx=0)
                cast_frame.pack_propagate(False)
                cast_container = ttk.Frame(cast_frame, padding=0)
                cast_container.pack(side=tk.TOP, pady=0)

                people = show.get('People', [])
                for i, person in enumerate(people[:5]):
                    cast_photo = get_cast_image(person, width=90, height=148)
                    cast_member_frame = ttk.Frame(cast_container, width=135, padding=0)
                    cast_member_frame.pack(side=tk.LEFT, padx=2)
                    cast_label = ttk.Label(cast_member_frame, image=cast_photo, style="Cast.TLabel")
                    cast_label.image = cast_photo
                    cast_label.pack(side=tk.TOP, pady=(0, 0))
                    # Add click event to filter by actor
                    cast_label.bind("<Button-1>", lambda e, name=person.get('Name', 'Unknown'): self.set_search_mode_callback("actor", name))
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
                for i in range(len(people), 5):
                    cast_photo = ImageTk.PhotoImage(Image.new('RGB', (90, 148), color='#000000'))
                    cast_member_frame = ttk.Frame(cast_container, width=135, padding=0)
                    cast_member_frame.pack(side=tk.LEFT, padx=2)
                    cast_label = ttk.Label(cast_member_frame, image=cast_photo, style="Cast.TLabel")
                    cast_label.image = cast_photo
                    cast_label.pack(side=tk.TOP, pady=(0, 0))
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

                poster_frame = ttk.Frame(frame, width=129, style="DarkBlue.TFrame")
                poster_frame.pack(side=tk.RIGHT, fill='y', padx=2)
                poster_frame.pack_propagate(False)
                poster_container = ttk.Frame(poster_frame)
                poster_container.pack(expand=True)
                poster_img = get_image(show, width=129, height=184, image_type='Primary')
                poster_label = ttk.Label(poster_container, image=poster_img)
                poster_label.image = poster_img
                poster_label.pack()
                # Bind the poster image to open in Jellyfin web player
                poster_label.bind("<Button-1>", lambda e, id=show_id: self.on_poster_click(id))
        except Exception as e:
            print(f"Error in load_ordered_shows: {e}")
            raise

    def clear_frame_content(self, frame):
        """Clear all content inside the frame without hiding the frame itself."""
        if not frame.winfo_exists():
            return
        for widget in frame.winfo_children():
            widget.destroy()

    def on_thumb_click(self, item_id):
        # Find the frame (row) corresponding to the selected show
        selected_frame_index = None
        for idx, sid in self.show_ids.items():
            if sid == item_id:
                selected_frame_index = idx
                break

        if selected_frame_index is None:
            print(f"Could not find frame for show ID {item_id}")
            return

        # Show the loading indicator
        self.show_loading_indicator()

        # Clear content of all other frames immediately (delay set to 0)
        def update_ui():
            # Clear content of unselected rows
            for idx, frame in enumerate(self.show_frames):
                if idx != selected_frame_index and frame.winfo_exists():
                    self.clear_frame_content(frame)

        self.root.after(0, update_ui)  # Update UI immediately (delay = 0)

        # Launch the show in a separate thread
        def start_mpv():
            try:
                selected_episode_id = self.selected_episodes.get(item_id)
                if selected_episode_id:
                    launch_show(selected_episode_id)
                else:
                    launch_show(item_id)
            except Exception as e:
                print(f"Error launching show with ID {item_id}: {e}")

        # Start MPV in a separate thread
        threading.Thread(target=start_mpv, daemon=True).start()

        # After 4 seconds, close the main UI (changed from 5s to 4s)
        self.root.after(4000, self.close_ui)

    def on_poster_click(self, item_id):
        # Find the frame (row) corresponding to the selected show
        selected_frame_index = None
        for idx, sid in self.show_ids.items():
            if sid == item_id:
                selected_frame_index = idx
                break

        if selected_frame_index is None:
            print(f"Could not find frame for show ID {item_id}")
            return

        # Show the loading indicator
        self.show_loading_indicator()

        # Clear content of all other frames immediately (delay set to 0)
        def update_ui():
            # Clear content of unselected rows
            for idx, frame in enumerate(self.show_frames):
                if idx != selected_frame_index and frame.winfo_exists():
                    self.clear_frame_content(frame)

        self.root.after(0, update_ui)  # Update UI immediately (delay = 0)

        # Launch the show in Jellyfin web player in a separate thread
        def open_in_browser():
            try:
                # Construct the Jellyfin web player URL
                jellyfin_url = f"http://localhost:8096/web/index.html#!/details?id={item_id}&serverId={self.server_id}"
                print(f"Opening Jellyfin web player for item {item_id}: {jellyfin_url}")
                webbrowser.open(jellyfin_url)  # Opens in default browser with default audio device
            except Exception as e:
                print(f"Error opening Jellyfin web player for item {item_id}: {e}")

        # Start browser in a separate thread
        threading.Thread(target=open_in_browser, daemon=True).start()

        # After 4 seconds, close the main UI (changed from 5s to 4s)
        self.root.after(4000, self.close_ui)

    def close_ui(self):
        """Close the main UI while keeping MPV running."""
        self.hide_loading_indicator()  # Stop flashing and hide the loading label
        print("Closing main UI...")
        self.root.quit()
        self.root.destroy()
        print("Main UI closed.")

    def get_channel_image(self, channel):
        img_path = os.path.join("Channels", f"{channel}.png")
        width, height = 141, 184
        if os.path.exists(img_path):
            return ImageTk.PhotoImage(Image.open(img_path).resize((width, height), Image.Resampling.LANCZOS))
        return ImageTk.PhotoImage(Image.new('RGB', (width, height), color='#000000'))