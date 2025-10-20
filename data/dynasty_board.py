"""
This module is responsible for creating a dynasty draft board.

It scrapes dynasty Average Draft Position (ADP) data from FantasyPros and combines
it with full-season projected fantasy points to create a comprehensive board
for dynasty league drafts or offseason evaluation.
"""
import pandas as pd
import requests
import re
import json

from data.projections import compute_projected_points
from data.league_info import get_league_info

def create_draft_board(pos: str, league_id: str, owner_id: str, show_taken: bool = False) -> pd.DataFrame:
    """
    Creates a dynasty draft board by merging ADP rankings and projected points.

    This function fetches dynasty ADP and calculated full-season fantasy points,
    then merges them. It can optionally filter out players who are already on
    other teams' rosters in the specified league.

    Args:
        pos (str): The player position to create the board for (e.g., 'qb', 'rb').
        league_id (str): The unique identifier for the Sleeper league.
        owner_id (str): The user's owner ID, used to identify other owners' players.
        show_taken (bool, optional): If False, removes players on other rosters.
                                     If True, includes all players. Defaults to False.

    Returns:
        pd.DataFrame: A DataFrame containing merged ADP and projection data.
    """

    adp_df = get_adp(pos)
    # draft=True ensures we get full-season projections, not weekly ones.
    proj_df = compute_projected_points(pos, league_id, draft=True)
    board_df = adp_df.merge(proj_df, how='left', on='Player')

    if not show_taken:
        # Get the rosters of all other owners
        league_df = get_league_info(league_id)
        other_owners_df = league_df[league_df['owner_id'] != owner_id]

        # Create a single set of all players taken by other owners
        taken_fp_ids = set()
        for fp_id in other_owners_df['fantasypros_ids']:
            taken_fp_ids.update(fp_id)

        # Filter the projected players to exclude those taken by others
        board_df = board_df[~board_df['fantasypros_id'].isin(taken_fp_ids)]

    # Drop the ID column as it's only used for internal filtering and not needed in the final display.
    board_df.drop('fantasypros_id', axis=1, inplace=True)

    return board_df

def get_adp(pos: str) -> pd.DataFrame:
    """
    Scrapes dynasty Average Draft Position (ADP) data from FantasyPros.

    Constructs the FantasyPros URL for dynasty rankings, scrapes the page,
    and parses the embedded JSON data to create a clean DataFrame.

    Args:
        pos (str): The player position to retrieve ADP for (e.g., 'qb', 'rb').

    Returns:
        pd.DataFrame: A DataFrame with player ADP and related ranking data.
    """

    if pos not in ['qb', 'rb', 'wr', 'te']:
        raise Exception(f'Dynasty ADP data retrieval failed. Invalid position: {pos}. Must be qb, rb, wr, or te. ')

    # Construct the URL for dynasty rankings (differs from weekly rankings).
    adp_url = f'https://www.fantasypros.com/nfl/rankings/dynasty-{pos}.php'

    # Scrape the page content to find the embedded JSON data within a JavaScript variable.
    adp_response = requests.get(adp_url)
    adp_match = re.search(r'var ecrData = (\{.*?\});', adp_response.text)
    if not adp_match:
        raise Exception(f'Cannot find ADP data in {adp_url}.')

    # Extract and parse the JSON data.
    adp_json = adp_match.group(1)
    adp_data = json.loads(adp_json)
    players_list = (adp_data.get('players', []))
    adp_df = pd.DataFrame(players_list)

    # Create a 'Player' column that matches the format from the projections module for merging.
    adp_df['Player'] = adp_df['player_name'] + ' ' + adp_df['player_team_id']

    # Select and rename columns for a clean, user-friendly final DataFrame.
    adp_columns = ['player_id', 'Player', 'player_age', 'pos_rank', 'rank_ave', 'rank_min', 'rank_max', 'rank_std']
    adp_df = adp_df[adp_columns]
    adp_df = adp_df.rename({'player_id': 'fantasypros_id',
                            'player_age': 'Age',
                            'pos_rank': 'Rank',
                            'rank_min': 'ECR Min',
                            'rank_max': 'ECR Max',
                            'rank_ave': 'ADP',
                            'rank_std': 'ECR Std'}, axis=1)

    # Standardize the ID to a string type to ensure consistent merging with other data sources.
    adp_df['fantasypros_id'] = adp_df['fantasypros_id'].astype(int).astype(str)

    return adp_df

if __name__ == '__main__':
    # For debugging: prevent pandas from truncating display
    pd.set_option('display.max_rows', None)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)

    league_id = input('Enter Sleeper platform league number (This is found in the sleeper url):')
    owner_id = input('Enter your Sleeper owner ID:')
    board_df = create_draft_board('rb', league_id, owner_id)
    print(board_df)