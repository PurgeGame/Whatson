import random
from jellyfin_utils import get_shows, USER_ID
from jellyfin_apiclient_python import JellyfinClient

client = JellyfinClient()
client.config.app('Whatson', '1.0', 'MomDevice', 'MomDeviceId')
client.config.data['auth.ssl'] = False
JELLYFIN_URL = 'http://localhost:8096'

class ContentManager:
    def __init__(self):
        self.all_items = []
        self.channel_assignments = {}
        self.ordered_list = []
        self.current_index = 0
        self.group_size = 5

    def fetch_all_items(self):
        """Fetch all shows and movies from Jellyfin and assign channels."""
        print("Fetching all content...")
        self.all_items = get_shows()
        for item in self.all_items:
            collections = self.get_collections_for_item(item['Id'])
            self.channel_assignments[item['Id']] = self.assign_channel(collections)
        self.order_content()

    def get_collections_for_item(self, item_id):
        """Fetch collections (BoxSets) for an item using Jellyfin API."""
        try:
            # Fetch the item's details to get its BoxSet IDs
            item = client.jellyfin.get_item(item_id)
            collections = []
            # Check if the item belongs to any BoxSets (collections)
            if 'ParentBackdropItemId' in item and item['ParentBackdropItemId']:
                parent_id = item['ParentBackdropItemId']
                parent_item = client.jellyfin.get_item(parent_id)
                if parent_item['Type'] == 'BoxSet':
                    collections.append(parent_item['Name'])
            # Fetch all BoxSets and check membership
            boxsets = client.jellyfin.user_items(params={
                'Recursive': True,
                'IncludeItemTypes': 'BoxSet',
                'Fields': 'Name'
            })['Items']
            for boxset in boxsets:
                boxset_items = client.jellyfin.user_items(params={
                    'ParentId': boxset['Id'],
                    'Recursive': True,
                    'IncludeItemTypes': 'Series,Movie'
                })['Items']
                if any(item['Id'] == item_id for item in boxset_items):
                    collections.append(boxset['Name'])
            return collections
        except Exception as e:
            print(f"Error fetching collections for item {item_id}: {e}")
            return []

    def assign_channel(self, collections):
        """Assign a channel based on collections, falling back to 'random'."""
        if not collections:
            return "random"
        return collections[0]  # Use the first collection as the channel

    def order_content(self):
        """Order the content list so no more than one show per channel in each group of 5."""
        # Group items by channel
        channel_groups = {}
        for item in self.all_items:
            channel = self.channel_assignments[item['Id']]
            if channel not in channel_groups:
                channel_groups[channel] = []
            channel_groups[channel].append(item)

        # Shuffle within each channel to randomize order
        for channel in channel_groups:
            random.shuffle(channel_groups[channel])

        # Interleave items from different channels
        self.ordered_list = []
        channels = list(channel_groups.keys())
        while any(channel_groups.values()):
            used_channels = set()
            group = []
            # Fill a group of 5 with at most one item per channel
            for _ in range(self.group_size):
                available_channels = [ch for ch in channels if ch not in used_channels and channel_groups[ch]]
                if not available_channels:
                    break  # No more unused channels available for this group
                channel = random.choice(available_channels)
                used_channels.add(channel)
                self.ordered_list.append(channel_groups[channel].pop(0))
            # Remove empty channels
            channels = [ch for ch in channels if channel_groups[ch]]

    def get_current_set(self):
        """Return the current set of 5 shows."""
        start = self.current_index
        end = min(start + self.group_size, len(self.ordered_list))
        return self.ordered_list[start:end]

    def scroll_down(self):
        """Move to the next set of 5 shows."""
        if self.current_index + self.group_size < len(self.ordered_list):
            self.current_index += self.group_size
            return True
        return False

    def scroll_up(self):
        """Move to the previous set of 5 shows."""
        if self.current_index - self.group_size >= 0:
            self.current_index -= self.group_size
            return True
        return False