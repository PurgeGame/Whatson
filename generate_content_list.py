import random
import json
import os
import argparse
from jellyfin_utils import get_shows, USER_ID, client

# Cache file path
CACHE_FILE = "boxset_cache.json"

def load_cached_boxsets():
    """Load cached BoxSet data from a file."""
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, 'r') as f:
                cache = json.load(f)
                print(f"Loaded {len(cache['boxsets'])} BoxSets from cache.")
                return cache['boxsets'], cache['item_to_boxsets']
        except Exception as e:
            print(f"Error loading cache: {e}")
    return None, None

def save_boxset_cache(boxsets, item_to_boxsets):
    """Save BoxSet data to a cache file."""
    cache = {
        'boxsets': boxsets,
        'item_to_boxsets': item_to_boxsets
    }
    try:
        with open(CACHE_FILE, 'w') as f:
            json.dump(cache, f, indent=2)
        print(f"Saved {len(boxsets)} BoxSets to cache.")
    except Exception as e:
        print(f"Error saving cache: {e}")

def fetch_boxsets():
    """Fetch all BoxSets and their items from Jellyfin."""
    try:
        # Fetch all BoxSets for the user
        boxsets = client.jellyfin.user_items(params={
            'Recursive': True,
            'IncludeItemTypes': 'BoxSet',
            'Fields': 'Name'
        })['Items']
        print(f"Found {len(boxsets)} BoxSets: {[boxset['Name'] for boxset in boxsets]}")

        # Map items to their BoxSets
        item_to_boxsets = {}
        for boxset in boxsets:
            boxset_id = boxset['Id']
            boxset_items = client.jellyfin.items(params={
                'ParentId': boxset_id,
                'Recursive': True,
                'IncludeItemTypes': 'Series,Movie',
                'Fields': 'Name'
            })['Items']
            print(f"BoxSet {boxset['Name']} contains {len(boxset_items)} items: {[item['Name'] for item in boxset_items]}")
            for item in boxset_items:
                item_id = item['Id']
                if item_id not in item_to_boxsets:
                    item_to_boxsets[item_id] = []
                item_to_boxsets[item_id].append(boxset['Name'])

        # Add "Random" as a possible channel for every item
        for item_id in item_to_boxsets:
            if "Random" not in item_to_boxsets[item_id]:
                item_to_boxsets[item_id].append("Random")

        return boxsets, item_to_boxsets
    except Exception as e:
        print(f"Error fetching BoxSets: {e}")
        return [], {}

def fetch_all_items():
    """Fetch all shows and movies from Jellyfin."""
    print("Fetching all content...")
    return get_shows()

def get_collections_for_item(item_id, item_to_boxsets):
    """Get collections for an item using the cached item-to-boxsets mapping."""
    collections = item_to_boxsets.get(item_id, ["Random"])  # Default to ["Random"] if not found
    # Ensure "Random" is always in the list
    if "Random" not in collections:
        collections.append("Random")
    print(f"Item {item_id} possible channels: {collections}")
    return collections

def assign_channel(collections):
    """Randomly assign a channel from the list of possible channels."""
    if not collections:
        print("No channels found (should not happen, 'Random' should always be present).")
        return "Random"
    chosen_channel = random.choice(collections)  # Randomly select one channel
    print(f"Randomly assigned channel: {chosen_channel}")
    return chosen_channel

def order_content(all_items, channel_assignments):
    """Order the content list so no more than one show per channel in each group of 5."""
    # Group items by channel
    channel_groups = {}
    for item in all_items:
        channel = channel_assignments[item['Id']]
        if channel not in channel_groups:
            channel_groups[channel] = []
        channel_groups[channel].append(item)

    # Shuffle within each channel to randomize order
    for channel in channel_groups:
        random.shuffle(channel_groups[channel])

    # Interleave items from different channels
    ordered_list = []
    channels = list(channel_groups.keys())
    group_size = 5
    while any(channel_groups.values()):
        used_channels = set()
        for _ in range(group_size):
            available_channels = [ch for ch in channels if ch not in used_channels and channel_groups[ch]]
            if not available_channels:
                break  # No more unused channels available for this group
            channel = random.choice(available_channels)
            used_channels.add(channel)
            ordered_list.append(channel_groups[channel].pop(0))
        # Remove empty channels
        channels = [ch for ch in channels if channel_groups[ch]]

    return ordered_list

def main(refresh_cache=False):
    # Load cached BoxSet data if available and not refreshing
    if not refresh_cache:
        cached_boxsets, cached_item_to_boxsets = load_cached_boxsets()
    else:
        cached_boxsets, cached_item_to_boxsets = None, None

    # Fetch BoxSets if cache is missing or refresh is requested
    if cached_boxsets is None or cached_item_to_boxsets is None:
        boxsets, item_to_boxsets = fetch_boxsets()
        save_boxset_cache(boxsets, item_to_boxsets)
    else:
        boxsets, item_to_boxsets = cached_boxsets, cached_item_to_boxsets

    # Fetch all content
    all_items = fetch_all_items()

    # Check for uncached items
    uncached_items = [item for item in all_items if item['Id'] not in item_to_boxsets]
    if uncached_items:
        print(f"Found {len(uncached_items)} uncached items. Fetching their collections...")
        for item in uncached_items:
            item_id = item['Id']
            try:
                # Fetch the item's details to check for collection membership
                item_details = client.jellyfin.get_item(item_id)
                print(f"Fetching collections for uncached item {item_id}: {item_details.get('Name', 'Unknown')}")
                collections = []
                for boxset in boxsets:
                    boxset_id = boxset['Id']
                    boxset_items = client.jellyfin.items(params={
                        'ParentId': boxset_id,
                        'Recursive': True,
                        'IncludeItemTypes': 'Series,Movie',
                        'Fields': 'Name'
                    })['Items']
                    if any(item['Id'] == item_id for item in boxset_items):
                        collections.append(boxset['Name'])
                        print(f"Item {item_id} found in BoxSet: {boxset['Name']}")
                # Always add "Random" as a possible channel
                if "Random" not in collections:
                    collections.append("Random")
                item_to_boxsets[item_id] = collections
            except Exception as e:
                print(f"Error fetching collections for item {item_id}: {e}")
                item_to_boxsets[item_id] = ["Random"]
        # Update the cache with new items
        save_boxset_cache(boxsets, item_to_boxsets)

    # Assign channels
    channel_assignments = {}
    for item in all_items:
        collections = get_collections_for_item(item['Id'], item_to_boxsets)
        channel_assignments[item['Id']] = assign_channel(collections)

    # Order the content
    ordered_list = order_content(all_items, channel_assignments)

    # Output the list, numbered
    print("\nList of Shows and Channels:")
    for i, item in enumerate(ordered_list, 1):
        name = item.get('Name', 'Unknown')
        channel = channel_assignments[item['Id']]
        print(f"{i}. {name} - Channel: {channel}")

if __name__ == "__main__":
    # Add command-line argument to refresh cache
    parser = argparse.ArgumentParser(description="Generate a list of shows with assigned channels.")
    parser.add_argument('--refresh-cache', action='store_true', help="Force refresh of the BoxSet cache.")
    args = parser.parse_args()

    main(refresh_cache=args.refresh_cache)