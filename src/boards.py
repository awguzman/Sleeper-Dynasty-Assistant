"""
This module is responsible for generating player ranking boards for the dashboard.

It uses the nflreadpy library to fetch pre-compiled ranking and projection data
from FantasyPros for either dynasty/draft purposes or for weekly matchups. It also
provides functions to filter it based on league rosters.
"""

import polars as pl

from src.league import get_league_info
from nflreadpy import load_ff_rankings, load_ff_playerids


def create_board(league_df: pl.DataFrame | None, draft: bool, positional = bool) -> pl.DataFrame:
    """
    Creates a full player ranking board for all positions.

    This function can generate three types of boards:
    1. A dynasty positional ranking draft board with full-season ECR, player ages, etc.
    2. A dynasty overall ranking draft board with the same information as above.
    3. A weekly projections board with in-season weekly ECR and projections.

    Args:
        league_df (pl.DataFrame | None): A DataFrame containing league ownership data from get_league_info(). If None, no owners are added.
        draft (bool): If True, creates a dynasty draft board.
                      If False, creates a weekly projections board.
        positional (bool): If True, creates a dynasty positional ranking board.
                        If False, creates a dynasty overall ranking board.

    Returns:
        pl.DataFrame: A Polars DataFrame containing the generated player board.
    """
    if draft:
        # --- Dynasty/Draft Board Logic ---
        board_df = load_ff_rankings(type = 'draft')
        if board_df.is_empty():
            return pl.DataFrame()

        board_columns = ['id', 'player', 'team', 'bye', 'ecr_type', 'pos',
                         'ecr', 'best', 'worst', 'sd', 'scrape_date']
        if positional:
            ecr_type = 'dp'  # 'dp' specifies dynasty positional rankings
        else:
            ecr_type = 'do' # 'do' specified dynasty overall rankings

        board_df = board_df[board_columns].filter(pl.col('pos').is_in(['QB', 'RB', 'WR', 'TE']))

        # Filter for dynasty rankings, but keep all positions.
        board_df = board_df.filter(pl.col('ecr_type') == ecr_type).drop('ecr_type')

        # Rename columns for a user-friendly final DataFrame.
        board_df = board_df.rename({
            'id': 'fantasypros_id',
            'player': 'Player',
            'team': 'Team',
            'bye': 'Bye',
            'ecr': 'ECR',
            'best': 'Best',
            'worst': 'Worst',
            'sd': 'Std'
        })

        # Add player ages.
        board_df = add_ages(board_df)

        # Re-select columns to ensure a consistent and logical order for display.
        board_df = board_df.select(['fantasypros_id', 'Player', 'pos', 'Team', 'Age', 'Bye', 'ECR', 'Best', 'Worst',
                                    'Std', 'scrape_date'])

    else:
        # --- Weekly Projections Board Logic ---
        board_df = load_ff_rankings(type='week')
        if board_df.is_empty():
            return pl.DataFrame()

        board_columns = ['fantasypros_id', 'player_name', 'team', 'pos', 'pos_rank', 'player_opponent',
                         'start_sit_grade', 'ecr', 'best', 'worst', 'sd', 'r2p_pts', 'scrape_date']
        board_df = board_df[board_columns].filter(pl.col('pos').is_in(['QB', 'RB', 'WR', 'TE']))

        # Rename columns for a user-friendly final DataFrame.
        board_df = board_df.rename({
            'player_name': 'Player',
            'team': 'Team',
            'pos_rank': 'Rank',
            'player_opponent': 'Opponent',
            'start_sit_grade': 'Start Grade',
            'ecr': 'ECR',
            'best': 'Best',
            'worst': 'Worst',
            'sd': 'Std',
            'r2p_pts': 'Proj. Points'
        })

        # Filter out players with low projected points.
        # board_df = board_df.filter(pl.col('Proj. Points') >= 1)


    # Add league ownership data
    board_df = add_owners(league_df, board_df)

    return board_df


def add_ages(board_df: pl.DataFrame) -> pl.DataFrame:
    """
    This function joins the input board with player ID data to add ages of players.

    Args:
        board_df (pl.DataFrame): The player board to add ages to.

    Returns:
        pl.DataFrame: The board with an 'Age' column added and columns reordered.
    """
    # Load only the necessary columns from the player IDs data
    players_df = load_ff_playerids().select(['fantasypros_id', 'age'])

    # Perform a left join to add the 'age' column from players_df to board_df.
    board_df = board_df.join(players_df, on='fantasypros_id', how='left')

    # Rename the new column from 'age' to 'Age' for consistency.
    board_df = board_df.rename({'age': 'Age'})

    return board_df

def add_owners(league_df: pl.DataFrame | None, board_df: pl.DataFrame) -> pl.DataFrame:
    """
    Adds an "Owner" column based on league roster data to the player board.

    Args:
        league_df (pl.DataFrame | None): A DataFrame containing league ownership data from get_league_info().
        board_df (pl.DataFrame): The player board to add owners to.

    Returns:
        pl.DataFrame: The board with an 'Owner' column added.
    """

    if league_df is None or league_df.is_empty():
        # If no league_id, add placeholder Owner column.
        board_df = board_df.with_columns(pl.lit('N/A').alias('Owner'))
        return board_df

    if 'fantasypros_id' in board_df.columns:
        # Create a mapping from fantasypros_ids to owner_name.
        owner_map = league_df.select(['owner_name', 'fantasypros_ids']).explode('fantasypros_ids')
        owner_map = owner_map.rename({'owner_name': 'Owner', 'fantasypros_ids': 'fantasypros_id'})

        # Join owner_map to the player board.
        board_df = board_df.join(owner_map, on='fantasypros_id', how='left')

        # Drop duplicate players generated from join.
        board_df = board_df.unique(subset=['fantasypros_id'], maintain_order=True)

    elif 'gsis_id' in board_df.columns:
        # Create a mapping from gsis_ids to owner_name.
        owner_map = league_df.select(['owner_name', 'gsis_ids']).explode('gsis_ids')
        owner_map = owner_map.rename({'owner_name': 'Owner', 'gsis_ids': 'gsis_id'})

        # Join owner_map to the player board.
        board_df = board_df.join(owner_map, on='gsis_id', how='left')

        # Drop duplicate players generated from join.
        board_df = board_df.unique(subset=['gsis_id'], maintain_order=True)

    # Fill in null values.
    board_df = board_df.with_columns(pl.col('Owner').fill_null('Free Agent'))


    return board_df


if __name__ == '__main__':
    pl.Config(tbl_rows=-1, tbl_cols=-1)

    league_id = input('Enter Sleeper platform league number (This is found in the sleeper url):')
    league_df = get_league_info(league_id)
    board_df = create_board(league_df, draft=True, positional=False)
    print(board_df)
