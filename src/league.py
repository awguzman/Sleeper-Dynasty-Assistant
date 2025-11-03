"""
This module provides functions to interact with the Sleeper API.

It is responsible for fetching league-specific information, including:
- Team rosters and player IDs.
- User/owner information (IDs and display names).
- League scoring settings.

This data is then processed and formatted into polars DataFrames or dictionaries
for use throughout the application.
"""

import polars as pl
import requests

from nflreadpy import load_ff_playerids


def get_league_info(league_id: str) -> pl.DataFrame:
    """
    Retrieves and processes fantasy football league data from the Sleeper API.

    Args:
        league_id (str): The unique identifier for the Sleeper league.

    Returns:
        pl.DataFrame: A DataFrame with one row per owner, containing their ID,
                      name, and lists of their players' IDs and names.
        NOTE: Both ID values are returns as ints! For some reason, nflreadpy does not standardize the types of these ID's.
    """
    sleeper_url = f'https://api.sleeper.app/v1/league/{league_id}/rosters'
    league_columns = ['owner_id', 'players', 'reserve']

    # Request league data from Sleeper and store in a DataFrame.
    response = requests.get(sleeper_url)
    if not response.status_code == 200:
            response.raise_for_status() # Raise exception for bad status code.
    league_data = response.json()
    if not league_data:
        raise ValueError(f'League ID {league_id} does not return any league data from Sleeper.')
    league_df = pl.DataFrame(league_data)[league_columns]
    league_df = league_df.with_columns(pl.col('reserve').fill_null(pl.lit([]))) # Fill null values from no IR players.

    # Combine active players and reserve players into a single list of sleeper_ids.
    league_df = league_df.with_columns((pl.col('players').list.concat(pl.col('reserve'))).alias('sleeper_ids'))
    league_df = league_df.cast({'sleeper_ids': pl.List(pl.Int64())}) # Cast as Int to match types used by nflreadpy.
    league_df = league_df.drop(['players', 'reserve'])

    # Load required player ID data from nflreadpy and create a lookup dictionary
    id_map_df = load_ff_playerids().select(['sleeper_id', 'fantasypros_id'])
    id_lookup = dict(zip(id_map_df['sleeper_id'].to_list(),
                         id_map_df['fantasypros_id'].to_list()
                ))

    def map_ids(sleeper_id_list):
        """
        Helper function to map a list of Sleeper IDs to FantasyPros IDs.
        """
        fantasypros_ids = []
        if sleeper_id_list is None:
            return []

        for sid in sleeper_id_list:
            # Look up the fantasypros_id
            fp_id = id_lookup.get(sid)
            # Only include the player if they were successfully found in both mappings.
            if fp_id is not None:
                fantasypros_ids.append(fp_id)

        return fantasypros_ids

    league_df = league_df.with_columns(
        pl.col('sleeper_ids').map_elements(map_ids, return_dtype=pl.List(pl.Int64())).alias('fantasypros_ids')
    )

    # Merge with owner data to add a readable 'owner_name' column.
    league_df = translate_owner_id(league_id).join(league_df, how='left', on='owner_id').drop_nulls()

    return league_df


def translate_owner_id(league_id: str) -> pl.DataFrame:
    """
    Request the league owner data from the Sleeper API to translate owner_id their username.

    Args:
        league_id (str): The unique identifier for the Sleeper league.

    Returns:
        pl.DataFrame: A DataFrame with 'owner_id' and 'owner_name' columns.
    """

    sleeper_url = f'https://api.sleeper.app/v1/league/{league_id}/users'

    # Request league owner data from Sleeper and store in a DataFrame.
    response = requests.get(sleeper_url)
    if not response.status_code == 200:
        response.raise_for_status()
    owners_data = response.json()
    if not owners_data:
        raise ValueError(f'League ID {league_id} does not return any league data from Sleeper.')

    owner_df = pl.DataFrame(owners_data)[['user_id', 'display_name']]
    owner_df = owner_df.rename({'user_id': 'owner_id', 'display_name': 'owner_name'})

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
    if not response.status_code == 200:
        response.raise_for_status()
    league_data = response.json()
    if not league_data:
        raise ValueError(f'League ID {league_id} does not return any league data from Sleeper.')
    scoring_weights = league_data['scoring_settings']

    return scoring_weights


if __name__ == '__main__':
    # pl.Config(tbl_rows=-1, tbl_cols=-1)

    league_id = input('Enter Sleeper platform league number (This is found in the sleeper url):')
    league_df = get_league_info(league_id)
    print(league_df)
