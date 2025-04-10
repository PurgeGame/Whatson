from jellyfin_apiclient_python import JellyfinClient
import csv

def get_jellyfin_shows(client, user_id):
    """
    Retrieves a list of shows from Jellyfin using the jellyfin_apiclient_python.

    Args:
        client (JellyfinClient): An authenticated JellyfinClient instance.
        user_id (str): The user ID.

    Returns:
        list: A list of dictionaries, where each dictionary represents a show.
              Returns None on failure.
    """
    try:
        items = client.jellyfin.items(parent_id=user_id, recursive=True, include_item_types="Series")
        shows = [{"Name": item.name} for item in items["Items"]]
        return shows

    except Exception as e:
        print(f"Error retrieving shows: {e}")
        return None

def shows_to_csv(shows, filename="jellyfin_shows.csv"):
    """
    Writes a list of shows to a CSV file.

    Args:
        shows (list): A list of dictionaries representing shows.
        filename (str): The name of the CSV file to create.
    """
    if not shows:
        return

    try:
        with open(filename, "w", newline="", encoding="utf-8") as csvfile:
            fieldnames = shows[0].keys()
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader()
            for show in shows:
                writer.writerow(show)
        print(f"Shows written to {filename}")

    except IOError as e:
        print(f"Error writing to CSV: {e}")

def main():
    """
    Main function to retrieve shows and write them to a CSV using JellyfinClient.
    """
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

    shows = get_jellyfin_shows(client, USER_ID)

    if shows:
        shows_to_csv(shows)
        print("You can now import the jellyfin_shows.csv file into Google Sheets.")
    else:
        print("Failed to retrieve shows.")

if __name__ == "__main__":
    main()