"""
This module serves as the master player ID mapping utility for the application.

Its primary function is to generate a clean, unified DataFrame that connects a player's
name and team to their unique identifiers on different platforms (Sleeper, FantasyPros).
This mapping is essential for merging disparate data sources, such as Sleeper rosters
and FantasyPros rankings/projections.
"""
import nfl_data_py as nfl
import pandas as pd


def get_id_map() -> pd.DataFrame:
    """
    Fetches and cleans a dataset to map player names to their platform-specific IDs.

    This function uses the nfl_data_py library as its source. It performs several
    cleaning steps: normalizing team abbreviations, creating a composite 'Player' key,
    and removing entries that lack the necessary IDs for mapping.

    Returns:
        pd.DataFrame: A clean DataFrame with 'Player', 'sleeper_id', and
                      'fantasypros_id' columns, ready for merging.
    """

    # Define the columns we want to keep from the imported data
    id_columns = ['name', 'team', 'sleeper_id', 'fantasypros_id']

    # Import the player ID data and select the specified columns
    id_map_df = nfl.import_ids()
    if id_map_df.empty:
        raise Exception('nfl_data_py ID import failed.')
    id_map_df = id_map_df[id_columns]


    # Normalize team abbreviations to match the format used by other data sources (e.g., FantasyPros).
    # nfl_data_py sometimes uses 3-letter codes (GBP) while others use 2 (GB).
    abbreviations = {'GBP': 'GB', 'KCC' : 'KC', 'LVR': 'LV', 'NEP': 'NE', 'NOS': 'NO', 'SFO': 'SF', 'TBB': 'TB'}
    id_map_df['team'] = id_map_df['team'].replace(abbreviations)

    # Create a 'Player' column by combining the player's name and team for a unique identifier
    # This helps differentiate between players with the same name but different teams.
    id_map_df.insert(loc=0, column='Player', value=id_map_df['name'] + ' ' + id_map_df['team'])

    # Drop the original 'name' and 'team' columns as they are now redundant
    id_map_df = id_map_df.drop(columns=['name', 'team'], axis=1)

    # Remove any players who are missing a Sleeper or FantasyPros ID, as they cannot be mapped
    id_map_df = id_map_df.dropna(subset=['sleeper_id', 'fantasypros_id']).reset_index(drop=True)

    # Convert ID columns to a string type to ensure consistent and reliable merging.
    # The .astype(int) step handles cases where IDs might be read as floats (e.g., '4046.0').
    id_map_df['sleeper_id'] = id_map_df['sleeper_id'].astype(int).astype(str)
    id_map_df['fantasypros_id'] = id_map_df['fantasypros_id'].astype(int).astype(str)

    return id_map_df


if __name__ == '__main__':
    # For debugging: prevent pandas from truncating display
    pd.set_option('display.max_rows', None)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)

    print(get_id_map().head())
