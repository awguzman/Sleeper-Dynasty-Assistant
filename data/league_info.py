"""
This module provides functions to interact with the Sleeper API.

It is responsible for fetching league-specific information, including:
- Team rosters and player IDs.
- User/owner information (IDs and display names).
- League scoring settings.

This data is then processed and formatted into pandas DataFrames or dictionaries
for use throughout the application.
"""
import pandas as pd
import requests
from data.id_map import get_id_map


def get_league_info(league_id: str) -> pd.DataFrame:
    """
    Retrieves and processes fantasy football league data from the Sleeper API.

    Args:
        league_id (str): The unique identifier for the Sleeper league.

    Returns:
        pd.DataFrame: A DataFrame with one row per owner, containing their ID,
                      name, and lists of their players' IDs and names.
    """
    sleeper_url = f'https://api.sleeper.app/v1/league/{league_id}/rosters'
    league_columns = ['owner_id', 'players', 'reserve']

    # Request league data from Sleeper and store in a DataFrame.
    response = requests.get(sleeper_url)
    response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)
    sleeper_rosters = response.json()
    if not sleeper_rosters:
        raise Exception(f'League ID {league_id} does not return any league data from Sleeper.')
    league_df = pd.DataFrame.from_dict(sleeper_rosters, orient='columns')[league_columns]


    # Combine active players and reserve players into a single list of sleeper_ids.
    # The `or []` handles cases where a roster might have no players or no reserves (e.g., None).
    league_df['sleeper_ids'] = league_df.apply(lambda row: (row['players'] or []) + (row['reserve'] or []), axis=1)
    league_df = league_df.drop(columns=['players', 'reserve'])

    # Create fast lookup dictionaries from the master ID map for efficient mapping.
    id_map_df = get_id_map()
    sleeper_to_fpro = pd.Series(id_map_df.fantasypros_id.values, index=id_map_df.sleeper_id).to_dict()
    sleeper_to_name = pd.Series(id_map_df.Player.values, index=id_map_df.sleeper_id).to_dict()

    def map_ids(sleeper_id_list):
        """
        Helper function to safely map a list of Sleeper IDs to FantasyPros IDs and names.

        It uses the pre-built dictionaries for fast lookups and skips any players
        that are not found in the master ID map.
        """
        fantasypros_ids = []
        player_names = []
        for sid in sleeper_id_list:
            # Look up the fantasypros_id and player_name
            fp_id = sleeper_to_fpro.get(sid)
            name = sleeper_to_name.get(sid)

            # Only include the player if they were successfully found in both mappings.
            if fp_id is not None and name is not None:
                fantasypros_ids.append(fp_id)
                player_names.append(name)

        return fantasypros_ids, player_names

    # Apply the mapping and create two new columns for the results
    # This efficiently creates new columns from the tuple returned by map_ids.
    mapped_data = league_df['sleeper_ids'].apply(map_ids)
    league_df[['fantasypros_ids', 'player_names']] = pd.DataFrame(
        mapped_data.tolist(), index=league_df.index
    )

    # Merge with owner data to add a human-readable 'owner_name' column.
    league_df = translate_owner_id(league_id).merge(league_df, how='left', on='owner_id').dropna()

    return league_df


def translate_owner_id(league_id: str) -> pd.DataFrame:
    """
    Request the league owner data from the Sleeper API to translate owner_id their username.

    Args:
        league_id (str): The unique identifier for the Sleeper league.

    Returns:
        pd.DataFrame: A DataFrame with 'owner_id' and 'owner_name' columns.
    """

    sleeper_url = f'https://api.sleeper.app/v1/league/{league_id}/users'

    # Request league owner data from Sleeper and store in a DataFrame.
    response = requests.get(sleeper_url)
    response.raise_for_status()
    sleeper_users = response.json()
    if not sleeper_users:
        raise Exception(f'League ID {league_id} does not return any league data from Sleeper.')
    owner_df = pd.DataFrame.from_dict(sleeper_users, orient='columns')[['user_id', 'display_name']]
    owner_df = owner_df.rename(columns={'user_id': 'owner_id', 'display_name': 'owner_name'})

    return owner_df

def get_scoring_weights(league_id: str) -> dict:
    """
    Gets the scoring settings for the Sleeper league ID.

    Args:
        league_id (str): The unique identifier for the Sleeper league.

    Returns:
        dict: A dictionary containing the league's scoring settings.
    """

    sleeper_url = f'https://api.sleeper.app/v1/league/{league_id}'

    # Request league information from Sleeper and select the scoring settings value.
    response = requests.get(sleeper_url)
    response.raise_for_status()
    league_data = response.json()
    scoring_weights = league_data['scoring_settings']

    return scoring_weights


if __name__ == '__main__':
    # For debugging: prevent pandas from truncating display
    pd.set_option('display.max_rows', None)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)

    league_id = input('Enter Sleeper platform league number (This is found in the sleeper url):')
    league_df = get_league_info(league_id)
    print(league_df)
