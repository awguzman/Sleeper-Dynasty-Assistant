import nfl_data_py as nfl
import pandas as pd


def get_id_map() -> pd.DataFrame:
    """
    Generates a DataFrame mapping player names and teams to their Sleeper and FantasyPros IDs.

    Returns:
        pd.DataFrame: A DataFrame with 'Player', 'sleeper_id', and 'fantasypros_id' columns.
    """

    # Define the columns we want to keep from the imported data
    id_columns = ['name', 'team', 'sleeper_id', 'fantasypros_id']

    # Import the player ID data and select the specified columns
    id_map_df = nfl.import_ids()
    if id_map_df.empty:
        raise Exception('nfl_data_py ID import failed.')
    id_map_df = id_map_df[id_columns]


    # Replace certain 3 letter team abbreviations with the more common 2 letter abbreviations (eg GBP -> GB)
    abbreviations = {'GBP': 'GB', 'KCC' : 'KC', 'LVR': 'LV', 'NEP': 'NE', 'NOS': 'NO', 'SFO': 'SF', 'TBB': 'TB'}
    id_map_df['team'] = id_map_df['team'].replace(abbreviations)

    # Create a 'Player' column by combining the player's name and team for a unique identifier
    # This helps differentiate between players with the same name but different teams.
    id_map_df.insert(loc=0, column='Player (Team)', value=id_map_df['name'] + ' ' + id_map_df['team'])

    # Drop the original 'name' and 'team' columns as they are now redundant
    id_map_df = id_map_df.drop(columns=['name', 'team'], axis=1)

    # Remove any players who are missing a Sleeper or FantasyPros ID, as they cannot be mapped
    id_map_df = id_map_df.dropna(subset=['sleeper_id', 'fantasypros_id']).reset_index(drop=True)

    return id_map_df


if __name__ == '__main__':
    # For debugging: prevent pandas from truncating display
    pd.set_option('display.max_rows', None)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)

    print(get_id_map().head())
