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
        pl.DataFrame: A DataFrame with one row per owner, containing their Owner ID,
                      username, and lists of their players' IDs.
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
    id_map_df = load_ff_playerids().select(['sleeper_id', 'fantasypros_id', 'gsis_id'])
    id_lookup = {row['sleeper_id']: {'fantasypros_id': row['fantasypros_id'], 'gsis_id': row['gsis_id']}
                 for row in id_map_df.iter_rows(named=True)}

    def map_sleeper_to_other_ids(sleeper_id_list):
        """
        Helper function to map a list of Sleeper IDs to FantasyPros IDs and GSIS IDs.
        Returns a dictionary (which Polars interprets as a Struct) of lists.
        """
        fantasypros_ids = []
        gsis_ids = []
        if sleeper_id_list is None:
            return {'fantasypros_ids': [], 'gsis_ids': []}

        for sid in sleeper_id_list:
            mapped_ids = id_lookup.get(sid)
            if mapped_ids:
                # Only append if the mapped ID is not None
                if mapped_ids['fantasypros_id'] is not None:
                    fantasypros_ids.append(mapped_ids['fantasypros_id'])
                if mapped_ids['gsis_id'] is not None:
                    gsis_ids.append(mapped_ids['gsis_id'])
        return {'fantasypros_ids': fantasypros_ids, 'gsis_ids': gsis_ids}

    # Apply the mapping function
    league_df = league_df.with_columns(
        pl.col('sleeper_ids').map_elements(
            map_sleeper_to_other_ids,
            return_dtype=pl.Struct([
                pl.Field("fantasypros_ids", pl.List(pl.Int64())),
                pl.Field("gsis_ids", pl.List(pl.String()))
            ])
        ).alias("mapped_ids_struct")
    )

    # Unpack the Struct column into separate columns and drop the temporary struct
    league_df = league_df.with_columns([
        pl.col("mapped_ids_struct").struct.field("fantasypros_ids").alias("fantasypros_ids"),
        pl.col("mapped_ids_struct").struct.field("gsis_ids").alias("gsis_ids")]
    )
    league_df = league_df.drop("mapped_ids_struct")

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
    Gets the scoring settings for the Sleeper league ID. Not used yet...

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
