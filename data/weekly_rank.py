import pandas as pd
import requests
import re
import json

from data.league_info import get_scoring_weights, get_league_info
from data.projections import compute_projected_points

def create_proj_board(pos:str, league_id: str, owner_id: str, show_taken = False) -> pd.DataFrame:

    rank_df = get_weekly_rank(pos, league_id)
    proj_df = compute_projected_points(pos, league_id, draft=False) # Retrieves current week projections

    board_df = rank_df.merge(proj_df, how='left', on='Player')

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


def get_weekly_rank(pos: str, league_id: str) -> pd.DataFrame:

    if pos not in ['qb', 'rb', 'wr', 'te']:
        raise Exception(f'Weekly projections data retrieval failed. Invalid position: {pos}. Must be qb, rb, wr, or te. ')

    # Store fantasypros url for projected ranks. Use league_info.py to get ppr settings from the given league.
    if pos == 'qb':
        rank_url = f'https://www.fantasypros.com/nfl/rankings/qb.php'
    else:
        scoring_weights = get_scoring_weights(league_id)
        if scoring_weights['rec'] == 1:
            ppr = 'ppr'
        elif scoring_weights['rec'] == 0.5:
            ppr = 'half-point-ppr'
        else:
            ppr = ''

        rank_url = f'https://www.fantasypros.com/nfl/rankings/{ppr}-{pos}.php'

    # Find the ecrData .JSON and Load it in as a DataFrame.
    rank_response = requests.get(rank_url)
    rank_match = re.search(r'var ecrData = (\{.*?\});', rank_response.text)
    if not rank_match:
        raise Exception(f'Cannot find proj data in {rank_url}.')

    rank_json = rank_match.group(1)
    rank_data = json.loads(rank_json)
    players_list = (rank_data.get('players', []))
    rank_df = pd.DataFrame(players_list)

    rank_df['Player'] = rank_df['player_name'] + ' ' + rank_df['player_team_id']
    proj_columns = ['player_id', 'Player', 'pos_rank', 'start_sit_grade', 'player_opponent', 'rank_ave', 'rank_min', 'rank_max', 'rank_std']
    rank_df = rank_df[proj_columns]
    rank_df = rank_df.rename({'player_id': 'fantasypros_id',
                            'pos_rank': 'Rank',
                            'start_sit_grade': 'Start',
                            'player_opponent': 'Opponent',
                            'rank_min': 'ECR Min',
                            'rank_max': 'ECR Max',
                            'rank_ave': 'ECR Avg',
                            'rank_std': 'ECR Std'}, axis=1)

    # Convert type of ID's to conform later.
    rank_df['fantasypros_id'] = rank_df['fantasypros_id'].astype(int).astype(str)

    return rank_df


if __name__ == '__main__':
    # For debugging: prevent pandas from truncating display
    pd.set_option('display.max_rows', None)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)

    league_id = input('Enter Sleeper platform league number (This is found in the sleeper url):')
    rb_df = create_proj_board('rb', league_id)
    print(rb_df)



