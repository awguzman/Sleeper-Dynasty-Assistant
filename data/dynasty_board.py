import pandas as pd
import requests
import re
import json


from data.projections import compute_projected_points
from data.league_info import get_league_info

def create_draft_board(pos:str, league_id: str, owner_id: str, show_taken = False) -> pd.DataFrame:

    adp_df = get_adp(pos)
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

    board_df.drop('fantasypros_id', axis=1, inplace=True)

    return board_df

def get_adp(pos: str) -> pd.DataFrame:
    """
    Get Fantasypros ADP Data for the given position.

    Args:
        pos: Position to retrieve ADP data for. Can only be qb, rb, wr, or te.

    Returns:
        A pandas DataFrame containing one row per player, with columns giving fantasypros_id, Player, Age, Position Rank,
        ECR Min, ECR Max, ADP, and ECR Std.
    """

    if pos not in ['qb', 'rb', 'wr', 'te']:
        raise Exception(f'Dynasty ADP data retrieval failed. Invalid position: {pos}. Must be qb, rb, wr, or te. ')

    adp_url = f'https://www.fantasypros.com/nfl/rankings/dynasty-{pos}.php'

    # Find the ecrData .JSON and Load it in as a DataFrame.
    adp_response = requests.get(adp_url)
    adp_match = re.search(r'var ecrData = (\{.*?\});', adp_response.text)
    if not adp_match:
        raise Exception(f'Cannot find ADP data in {adp_url}.')

    adp_json = adp_match.group(1)
    adp_data = json.loads(adp_json)
    players_list = (adp_data.get('players', []))
    adp_df = pd.DataFrame(players_list)

    # Reformat columns
    adp_df['Player'] = adp_df['player_name'] + ' ' + adp_df['player_team_id']
    adp_columns = ['player_id', 'Player', 'player_age', 'pos_rank', 'rank_ave', 'rank_min', 'rank_max', 'rank_std']
    adp_df = adp_df[adp_columns]
    adp_df = adp_df.rename({'player_id': 'fantasypros_id',
                            'player_age': 'Age',
                            'pos_rank': 'Rank',
                            'rank_min': 'ECR Min',
                            'rank_max': 'ECR Max',
                            'rank_ave': 'ADP',
                            'rank_std': 'ECR Std'}, axis=1)

    # Convert type of ID's to conform later.
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