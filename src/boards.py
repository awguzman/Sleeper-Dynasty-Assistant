"""
This module is responsible for generating player ranking boards for the dashboard.

It uses the nflreadpy library to fetch pre-compiled ranking and projection data
from FantasyPros for either dynasty/draft purposes or for weekly matchups. It also
provides functions to enrich this data and filter it based on league rosters.
"""

import polars as pl

from src.league_info import get_league_info
from nflreadpy import load_ff_rankings, load_ff_playerids
from src.tiers import create_tiers

def create_board(pos: str, draft: bool = False) -> pl.DataFrame:
    """
    Creates a player ranking board for a specific position.

    This function can generate two types of boards:
    1. A dynasty/draft board with full-season ECR, player ages, etc.
    2. A weekly board with in-season weekly ECR and projections.

    Args:
        pos (str): The position to create the board for (e.g., 'QB', 'RB').
        draft (bool, optional): If True, creates a dynasty/draft board.
                                If False, creates a weekly board. Defaults to False.

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
        ecr_type = 'dp'  # 'dp' specifies dynasty positional rankings
        board_df = board_df[board_columns]

        # Filter for the specified position and for dynasty rankings
        board_df = board_df.filter((pl.col('pos') == pos) &
                                   (pl.col('ecr_type') == ecr_type)).drop('pos', 'ecr_type')

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

        # Add player ages, which is critical for dynasty.
        board_df = add_ages(board_df)

    else:
        # --- Weekly Projections Board Logic ---
        board_df = load_ff_rankings(type='week')
        if board_df.is_empty():
            return pl.DataFrame()

        board_columns = ['fantasypros_id', 'player_name', 'team', 'pos', 'pos_rank', 'player_opponent',
                         'start_sit_grade', 'ecr', 'best', 'worst', 'sd', 'r2p_pts', 'scrape_date']
        board_df = board_df[board_columns]

        # Filter for the specified position
        board_df = board_df.filter((pl.col('pos') == pos)).drop('pos')

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

    # Cast ID column as a string to ensure consistent filtering with other data sources, like league rosters.
    board_df = board_df.cast({'fantasypros_id': pl.String()})

    # board_df = create_tiers(board_df, n_tiers=8)

    return board_df

def remove_taken(league_id: str, owner_id: str, board_df: pl.DataFrame) -> pl.DataFrame:
    """
    Filters a player board to remove players who are on other owners' rosters.

    Args:
        league_id (str): The Sleeper league ID.
        owner_id (str): The user's owner ID. Players on this roster will NOT be removed.
        board_df (pl.DataFrame): The player board to be filtered.

    Returns:
        pl.DataFrame: A filtered DataFrame containing only available players.
    """
    # Get the rosters of all other owners
    league_df = get_league_info(league_id)
    other_owners_df = league_df.filter(pl.col('owner_id') != owner_id)

    # Create a single set of all players taken by other owners
    taken_fp_ids = set()
    for fp_id in other_owners_df['fantasypros_ids']:
        taken_fp_ids.update(fp_id)

    # Filter the board to exclude players whose fantasypros_id is in the taken set.
    board_df = board_df.filter(~pl.col('fantasypros_id').is_in(taken_fp_ids))

    return board_df

def add_ages(board_df: pl.DataFrame) -> pl.DataFrame:
    """
    This function joins the input board with player ID data to add ages,
    which is particularly useful for dynasty/draft boards.

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

    # Re-select columns to ensure a consistent and logical order for display.
    board_df = board_df.select(['fantasypros_id', 'Player', 'Team', 'Age', 'Bye', 'ECR', 'Best', 'Worst',
                                'Std', 'scrape_date'])

    return board_df


if __name__ == '__main__':
    pl.Config(tbl_rows=-1, tbl_cols=-1)

    board_df = create_board('RB', draft=True)
    print(board_df)
