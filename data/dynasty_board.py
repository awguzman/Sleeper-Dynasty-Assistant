import pandas as pd

from data.season_proj import compute_projected_points
from data.dynasty_adp import get_adp

def create_draft_board(pos:str, league_id: str) -> pd.DataFrame:

    adp_df = get_adp(pos)
    proj_df = compute_projected_points(pos, league_id)

    board_df = adp_df.merge(proj_df, how='left', on='Player')

    return board_df

if __name__ == '__main__':
    # For debugging: prevent pandas from truncating display
    pd.set_option('display.max_rows', None)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)

    league_id = input('Enter Sleeper platform league number (This is found in the sleeper url):')
    board_df = create_draft_board('rb', league_id)
    print(board_df)