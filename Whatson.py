#!/usr/bin/env python3
import random
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk
import ttkbootstrap as tb
import os

from jellyfin_utils import get_shows, get_image, launch_show, open_jellyfin_ui, get_description, get_cast_image
from ui_utils import truncate_description, get_font_size

class WhatsonUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Whatson")

        # Set window dimensions directly
        original_width = 1920
        original_height = 600

        self.root.geometry(f"{original_width}x{original_height}")
        self.root.configure(bg='#121212')

        # Maximize the window on the primary monitor (Linux-compatible method)
        self.root.attributes('-zoomed', True)
        self.root.update_idletasks()
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        x = 0
        y = 0
        self.root.geometry(f"+{x}+{y}")

        self.shows = get_shows()
        self.filtered_shows = self.shows[:]

        self.color_scheme = {
            "bg": "#121212",
            "series": "#FFA500",  # Option 3: Orange
            "episode": "#ADFF2F",  # Option 3: Lime Green
            "desc": "#FFFFFF"
        }

        self.channel_logos = []
        channels_folder = "Channels"
        if os.path.exists(channels_folder):
            for file_name in os.listdir(channels_folder):
                if file_name.lower().endswith(('.png', '.jpg', '.jpeg', '.gif')):
                    try:
                        img_path = os.path.join(channels_folder, file_name)
                        row_height = 180
                        original_logo_width = 200
                        original_logo_height = 260
                        logo_height = row_height
                        aspect_ratio = original_logo_width / original_logo_height
                        logo_width = int(logo_height * aspect_ratio)  # 180 * (200/260) ≈ 138
                        img = Image.open(img_path).resize((logo_width, logo_height), Image.Resampling.LANCZOS)
                        photo = ImageTk.PhotoImage(img)
                        self.channel_logos.append(photo)
                    except Exception as e:
                        print(f"Error loading channel logo {file_name}: {e}")
        if not self.channel_logos:
            print("No channel logos found in Channels folder. Using placeholder text.")
            self.channel_logos = None

        top_frame = ttk.Frame(self.root, padding=5)
        top_frame.pack(fill='x', pady=5)

        try:
            logo_img = Image.open("path/to/logo.png")
            logo_img = logo_img.resize((40, 40), Image.Resampling.LANCZOS)
            self.logo = ImageTk.PhotoImage(logo_img)
            ttk.Label(top_frame, image=self.logo).pack(side=tk.LEFT, padx=10)
        except:
            ttk.Label(top_frame, text="[Logo]", font=('Helvetica', 14), foreground='#ffffff').pack(side=tk.LEFT, padx=10)

        ttk.Label(top_frame, text="Whatson", font=('Helvetica', 16, 'bold'), foreground='#ffffff').pack(side=tk.LEFT, padx=10)

        search_frame = ttk.Frame(top_frame)
        search_frame.pack(side=tk.LEFT, padx=20)
        ttk.Label(search_frame, text="Search Shows:", font=('Helvetica', 10), foreground='#ffffff').pack(side=tk.LEFT)
        self.filter_var = tk.StringVar()
        self.filter_entry = ttk.Entry(search_frame, textvariable=self.filter_var, width=50, font=('Helvetica', 8))
        self.filter_entry.pack(side=tk.LEFT, padx=10)
        self.filter_var.trace('w', self.filter_shows)

        main_frame = ttk.Frame(self.root, padding=10)
        main_frame.pack(fill='both', expand=True)

        self.show_frames = []
        for i in range(5):
            frame = ttk.Frame(main_frame, height=180, padding=5, style="DarkBlue.TFrame")
            frame.pack(fill='x', pady=2)
            frame.pack_propagate(False)
            self.show_frames.append(frame)

        self.load_random_shows()

    def filter_shows(self, *args):
        filter_text = self.filter_var.get().lower()
        self.filtered_shows = [
            show for show in self.shows
            if filter_text in show['Name'].lower() or
               filter_text in (show.get('Genres', []) and ','.join(show['Genres']).lower())
        ]
        self.load_random_shows()

    def clear_frames(self):
        for frame in self.show_frames:
            for widget in frame.winfo_children():
                widget.destroy()

    def load_random_shows(self):
        self.clear_frames()
        valid_shows = [
            show for show in self.filtered_shows
            if show.get('Name') and show.get('Name').strip()
            and show.get('People') and len(show.get('People')) > 0
        ]
        selected_shows = random.sample(valid_shows, min(5, len(valid_shows)))
        self.current_shows = selected_shows

        scheme = self.color_scheme

        if self.channel_logos:
            num_logos = min(len(self.channel_logos), 5)
            selected_logos = random.sample(self.channel_logos, num_logos)
            selected_logos.extend([None] * (5 - num_logos))
        else:
            selected_logos = [None] * 5

        for frame, show, logo in zip(self.show_frames, self.current_shows, selected_logos):
            if logo:
                channel_logo = ttk.Label(frame, image=logo)
                channel_logo.image = logo
                channel_logo.pack(side=tk.LEFT, padx=2)
            else:
                channel_logo = ttk.Label(frame, text="[Channel Logo]", width=15, anchor='center', 
                                        foreground=scheme["desc"], style="DarkBlue.TLabel")
                channel_logo.pack(side=tk.LEFT, padx=2)

            img = get_image(show, width=320, height=180, image_type='Thumb')
            img_label = ttk.Label(frame, image=img)
            img_label.image = img
            img_label.pack(side=tk.LEFT, padx=2)

            description_frame = ttk.Frame(frame, width=720, style="DarkBlue.TFrame")  # Reduced width to 600
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
                    desc_text.insert(tk.END, " ", "spacer")
                    desc_text.insert(tk.END, episode_prefix, "episode_prefix")
                    if episode_name:
                        desc_text.insert(tk.END, ": ", "episode_prefix")
                        desc_text.insert(tk.END, episode_name, "episode_name")
                    desc_text.insert(tk.END, ".", "period")
                    desc_text.insert(tk.END, " ", "description")
                    desc_text.insert(tk.END, description, "description")
                else:
                    desc_text.insert(tk.END, show_title.upper(), "series_name")
                    desc_text.insert(tk.END, " ", "spacer")
                    desc_text.insert(tk.END, episode_title, "episode_prefix")
                    desc_text.insert(tk.END, ".", "period")
                    desc_text.insert(tk.END, " ", "description")
                    desc_text.insert(tk.END, description, "description")
            else:
                desc_text.insert(tk.END, show_title.upper(), "series_name")
                desc_text.insert(tk.END, " ", "spacer")
                desc_part = description
                if description.startswith(show_title.upper() + " "):
                    desc_part = description[len(show_title.upper()) + 1:]
                desc_text.insert(tk.END, desc_part, "description")

            desc_text.tag_configure("center", justify='left')
            desc_text.tag_add("center", "1.0", "end")
            desc_text.configure(state='disabled')

            cast_frame = ttk.Frame(frame, width=480, style="DarkBlue.TFrame")  # Increased width to 600
            cast_frame.pack(side=tk.LEFT, fill='y', padx=0)
            cast_frame.pack_propagate(False)
            cast_container = ttk.Frame(cast_frame)
            cast_container.pack(side=tk.TOP, pady=0)

            people = show.get('People', [])
            for person in people[:5]:
                cast_photo = get_cast_image(person, width=123, height=130)
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
                    foreground=scheme["desc"],
                    justify='center',
                    anchor='center',
                    compound='text',
                    style="DarkBlue.TLabel"
                )
                name_label.pack(side=tk.TOP, pady=(0, 0))

            poster_frame = ttk.Frame(frame, width=125, style="DarkBlue.TFrame")
            poster_frame.pack(side=tk.RIGHT, fill='y', padx=2)
            poster_frame.pack_propagate(False)
            poster_container = ttk.Frame(poster_frame)
            poster_container.pack(expand=True)
            poster_img = get_image(show, width=125, height=180, image_type='Primary')
            poster_label = ttk.Label(poster_container, image=poster_img)
            poster_label.image = poster_img
            poster_label.pack()
            poster_label.bind("<Button-1>", lambda e, id=show['Id']: launch_show(id))

    def filter_shows(self, *args):
        filter_text = self.filter_var.get().lower()
        self.filtered_shows = [
            show for show in self.shows
            if filter_text in show['Name'].lower() or
               filter_text in (show.get('Genres', []) and ','.join(show['Genres']).lower())
        ]
        self.load_random_shows()

if __name__ == "__main__":
    root = tb.Window(themename="cyborg")
    style = ttk.Style()
    style.configure("DarkBlue.TFrame", background="#0A1A2F")
    style.configure("DarkBlue.TLabel", background="#0A1A2F", foreground="#ffffff")
    app = WhatsonUI(root)
    root.mainloop()