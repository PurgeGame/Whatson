# ui_utils.py

def truncate_description(description):
    """Truncate the description to 600 characters (including spaces) if it exceeds the limit."""
    if len(description) > 600:
        return description[:597] + "..."
    return description

def get_font_size(description, series_title, episode_title=None):
    """
    Determine the font sizes for the series title and description based on content length.
    Returns a tuple of (series_font_size, desc_font_size, reduce_title).
    """
    desc_length = len(description)
    series_length = len(series_title)
    if episode_title:
        desc_length += len(episode_title) + 2  # Account for episode title and ": "

    # Base font sizes
    base_series_font_size = 28
    base_desc_font_size = 20

    # Adjust based on description length
    if desc_length > 550:
        desc_font_size = 15
    elif desc_length > 450:
        desc_font_size = 17
    elif desc_length > 400:
        desc_font_size = 18
    else:
        desc_font_size = 19
    
    series_font_size = 19

    # Adjust series title font size based on description font size and series title length
    """     if series_length > 30:
        
    else:
        series_font_size = max(base_series_font_size - (20 - desc_font_size), desc_font_size + 2) """

    reduce_title = desc_length > 420

    return series_font_size, desc_font_size, reduce_title