#!/usr/bin/env python3
import random
import ttkbootstrap as tb
import tkinter as tk
from tkinter import ttk
import traceback

from whatson_ui import WhatsonUI
from generate_content_list import fetch_all_items, load_cached_boxsets, get_collections_for_item, order_content

class WhatsonApp:
    def __init__(self):
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

        # Assign channels
        self.channel_assignments = {}
        for item in self.shows:
            collections = get_collections_for_item(item['Id'], self.item_to_boxsets)
            non_random_channels = [channel for channel in collections if channel != "Random"]
            if non_random_channels:
                selected_channel = random.choice(non_random_channels)
            else:
                selected_channel = "Random"
            self.channel_assignments[item['Id']] = selected_channel
            print(f"Assigned channel for {item.get('Name', 'Unknown')} (ID: {item['Id']}): {selected_channel} from {collections}")

        # Order the content list (randomized order, max one channel per group of 5)
        self.ordered_shows = order_content(self.shows, self.channel_assignments)

        # Post-process to ensure no more than one instance of a channel per 5 entries
        chunk_size = 5
        for i in range(0, len(self.ordered_shows), chunk_size):
            chunk = self.ordered_shows[i:i + chunk_size]
            chunk_channels = [self.channel_assignments[show['Id']] for show in chunk]
            channel_counts = {}
            for channel in chunk_channels:
                channel_counts[channel] = channel_counts.get(channel, 0) + 1
            duplicates = {channel: count for channel, count in channel_counts.items() if count > 1 and channel != "Random"}
            if duplicates:
                print(f"Found duplicate channels in chunk {i//chunk_size}: {duplicates}")
                for channel, count in duplicates.items():
                    for j, show in enumerate(chunk):
                        if self.channel_assignments[show['Id']] == channel and count > 1:
                            collections = get_collections_for_item(show['Id'], self.item_to_boxsets)
                            if "Random" in collections:
                                self.channel_assignments[show['Id']] = "Random"
                                print(f"Reassigned {show.get('Name', 'Unknown')} (ID: {show['Id']}) to Random to resolve duplicate {channel}")
                                count -= 1
                self.ordered_shows = order_content(self.shows, self.channel_assignments)

        # Initialize filtered_shows as a copy of ordered_shows to respect the channel ordering
        self.filtered_shows = self.ordered_shows[:]

        # Initialize the current page
        self.current_page = 0
        self.shows_per_page = 5  # Number of shows displayed per page

        # Initialize search mode (title, actor, or channel)
        self.search_mode = "title"  # Default mode is title search

        # Initialize the UI
        self.root = tb.Window(themename="cyborg")
        style = ttk.Style()
        style.configure("DarkBlue.TFrame", background="#0A1A2F")
        style.configure("DarkBlue.TLabel", background="#0A1A2F", foreground="#ffffff")
        style.configure("Cast.TLabel", background="#333333", foreground="#ffffff", padding=0)
        style.configure("Arrow.TButton", font=('Helvetica', 24), foreground="#ffffff", background="#555555", padding=5)
        style.configure("Large.TEntry", padding=10)

        self.ui = WhatsonUI(
            self.root,
            self.color_scheme,
            self.scroll_up,
            self.scroll_down,
            self.filter_shows,
            self.set_search_mode  # Pass the set_search_mode callback
        )
        self.load_ordered_shows()

    def filter_shows(self, *args):
        search_term = self.ui.filter_var.get().lower()
        if not search_term:
            # If the search term is empty, reset to the original ordered list
            self.search_mode = "title"  # Reset search mode
            self.filtered_shows = self.ordered_shows[:]
            self.current_page = 0  # Reset to the first page
            self.load_ordered_shows()
            return

        filtered_shows = []
        if self.search_mode == "actor":
            # Filter by actor name
            for show in self.ordered_shows:
                people = show.get('People', [])
                for person in people:
                    if search_term in person.get('Name', '').lower():
                        filtered_shows.append(show)
                        break
        elif self.search_mode == "channel":
            # Filter by channel name
            filtered_shows = [
                show for show in self.ordered_shows
                if self.channel_assignments[show['Id']].lower() == search_term
            ]
        else:
            # Default title search
            filtered_shows = [
                show for show in self.ordered_shows
                if search_term in show.get('Name', '').lower()
            ]

        self.filtered_shows = filtered_shows
        self.current_page = 0  # Reset to the first page of filtered results
        self.load_ordered_shows()

    def set_search_mode(self, mode, term):
        """Set the search mode (title, actor, or channel) and populate the search bar."""
        self.search_mode = mode
        self.ui.filter_var.set(term)
        self.filter_shows()

    def scroll_up(self, event=None):
        if self.current_page > 0:
            self.current_page -= 1
            print(f"Scrolled up to page {self.current_page}")
            self.load_ordered_shows()

    def scroll_down(self, event=None):
        total_pages = (len(self.filtered_shows) + self.shows_per_page - 1) // self.shows_per_page
        if self.current_page < total_pages - 1:
            self.current_page += 1
            print(f"Scrolled down to page {self.current_page}")
            self.load_ordered_shows()

    def load_ordered_shows(self):
        start_index = self.current_page * self.shows_per_page
        end_index = start_index + self.shows_per_page
        valid_shows = [
            show for show in self.filtered_shows
            if show.get('Name') and show.get('Name').strip()
        ]
        selected_shows = valid_shows[start_index:end_index]
        self.current_shows = selected_shows
        self.ui.load_ordered_shows(self.current_shows, self.channel_assignments)

    def run(self):
        print("Starting Tkinter main loop...")
        self.root.mainloop()
        print("Application closed.")

if __name__ == "__main__":
    try:
        print("Starting Whatson application...")
        app = WhatsonApp()
        app.run()
    except Exception as e:
        print(f"Error starting application: {e}")
        traceback.print_exc()