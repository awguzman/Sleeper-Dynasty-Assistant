import pandas as pd

from data.season_proj import compute_projected_points
from data.dynasty_adp import get_adp
from data.league_info import get_league_info

def create_draft_board(pos:str, league_id: str, owner_id: str) -> pd.DataFrame:

    adp_df = get_adp(pos)
    proj_df = compute_projected_points(pos, league_id)

    board_df = adp_df.merge(proj_df, how='left', on='Player')

    # Get the rosters of all other owners
    league_df = get_league_info(league_id)
    other_owners_df = league_df[league_df['owner_id'] != owner_id]

    # Create a single set of all players taken by other owners
    taken_fp_ids = set()
    for fp_id in other_owners_df['fantasypros_ids']:
        taken_fp_ids.update(fp_id)

    # Filter the projected players to exclude those taken by others
    board_df = board_df[~board_df['fantasypros_id'].isin(taken_fp_ids)]

    return board_df

if __name__ == '__main__':
    # For debugging: prevent pandas from truncating display
    pd.set_option('display.max_rows', None)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)

    league_id = input('Enter Sleeper platform league number (This is found in the sleeper url):')
    owner_id = input('Enter your Sleeper owner ID:')
    board_df = create_draft_board('rb', league_id, owner_id)
    print(board_df)