import pandas as pd
import requests
from data.id_map import get_id_map


def get_league_info(league_id: str) -> pd.DataFrame:
    """
    Retrieves and processes fantasy football league data from the Sleeper API.

    Args:
        league_id: The unique identifier for the Sleeper league.

    Returns:
        A pandas DataFrame containing one row per team owner, with columns for
        'owner_id', a list of 'sleeper_ids', a list of 'player_names', and a
        list of 'fantasypros_ids'.
    """
    sleeper_url = f'https://api.sleeper.app/v1/league/{league_id}/rosters'
    league_columns = ['owner_id', 'players', 'reserve']

    # Request league data from Sleeper and store in a DataFrame.
    sleeper_request = requests.get(sleeper_url).json()
    if sleeper_request == {}:
        raise Exception(f'League ID {league_id} does not return any league data from Sleeper.')
    league_df = pd.DataFrame.from_dict(sleeper_request, orient='columns')[league_columns]

    # Combine players and reserve into a single 'sleeper_ids' list for each owner
    league_df['sleeper_ids'] = league_df.apply(lambda row: (row['players'] or []) + (row['reserve'] or []), axis=1)
    league_df = league_df.drop(columns=['players', 'reserve'])

    # Get the player ID map and create lookup dictionaries
    id_map_df = get_id_map()
    sleeper_to_fp_dict = pd.Series(id_map_df.fantasypros_id.values, index=id_map_df.sleeper_id).to_dict()
    sleeper_to_name_dict = pd.Series(id_map_df.Player.values, index=id_map_df.sleeper_id).to_dict()

    # Helper function to use the dictionaries to map the sleeper_ids to the desired values
    def map_ids(sleeper_id_list):
        fantasypros_ids = [int(sleeper_to_fp_dict.get(int(sid))) for sid in sleeper_id_list]
        roster = [sleeper_to_name_dict.get(int(sid)) for sid in sleeper_id_list]
        return fantasypros_ids, roster

    # Apply the mapping and create two new columns for the results
    mapped_data = league_df['sleeper_ids'].apply(map_ids)
    league_df[['fantasypros_ids', 'roster']] = pd.DataFrame(mapped_data.tolist(), index=league_df.index)

    # Add owner name column.
    league_df = translate_owner_id(league_id).merge(league_df, how='left', on='owner_id').dropna()

    return league_df


def translate_owner_id(league_id: str) -> pd.DataFrame:
    """
    Request the league owner data from the Sleeper API to translate owner_id their username.

    Args:
        league_id: The unique identifier for the Sleeper league.

    Returns:
        A pandas DataFrame containing one row per team owner, with columns for
        'owner_id', 'owner_name' giving their Sleeper username.
    """

    sleeper_url = f'https://api.sleeper.app/v1/league/{league_id}/users'

    # Request league owner data from Sleeper and store in a DataFrame.
    sleeper_request = requests.get(sleeper_url).json()
    if sleeper_request == {}:
        raise Exception(f'League ID {league_id} does not return any league data from Sleeper.')
    owner_df = pd.DataFrame.from_dict(sleeper_request, orient='columns')[['user_id', 'display_name']]
    owner_df = owner_df.rename(columns={'user_id': 'owner_id', 'display_name': 'owner_name'})

    return owner_df


if __name__ == '__main__':
    # For debugging: prevent pandas from truncating display
    pd.set_option('display.max_rows', None)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)

    league_id = input('Enter Sleeper platform league number (This is found in the sleeper url):')
    league_df = get_league_info(league_id)
    print(league_df)
