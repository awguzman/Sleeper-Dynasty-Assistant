import nfl_data_py as nfl
import pandas as pd


def get_id_map() -> pd.DataFrame:
    """
    Generates a DataFrame mapping player names and teams to their Sleeper and FantasyPros IDs.

    The function performs the following steps:
    1. Imports player ID data from nfl_data_py and Selects the relevant ID columns
    2. Selects the relevant ID columns ('name', 'team', 'sleeper_id', 'fantasypros_id').
    3. Creates a composite 'Player' column (e.g., "Dan Marino MIA").
    4. Removes rows where either 'sleeper_id' or 'fantasypros_id' is missing.
    5. Resets the DataFrame index.

    Returns:
        pd.DataFrame: A DataFrame with 'Player', 'sleeper_id', and 'fantasypros_id' columns.
    """

    # Define the columns we want to keep from the imported data
    id_columns = ['name', 'team', 'sleeper_id', 'fantasypros_id']

    # Import the player ID data and select the specified columns
    id_map_df = nfl.import_ids()[id_columns]

    # Create a 'Player' column by combining the player's name and team for a unique identifier
    # This helps differentiate between players with the same name but different teams.
    id_map_df.insert(loc=0, column='Player', value=id_map_df['name'] + ' ' + id_map_df['team'])

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

    # Example of how to use the function and display the output
    player_id_map = get_id_map()
    print("Generated Player ID Map:")
    print(player_id_map.head())
    print(f"\nTotal players mapped: {len(player_id_map)}")
