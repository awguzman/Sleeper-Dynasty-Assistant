"""
This module is responsible for calculating and assigning trade values to players.

It takes a pre-processed player board, applies an exponential scaling algorithm
to the Expert Consensus Ranks (ECR) to generate a non-linear trade value.
"""

import polars as pl

from nflreadpy import load_ff_rankings
from src.boards import add_ages, add_owners

def create_trade_values(board_df: pl.DataFrame, league_id: str | None, inseason: bool = False) -> pl.DataFrame:
    """
    Creates a trade value board.

    This function takes a board DataFrame (typically from the dashboard's data store),
    adds data like ages and ownership, and then calculates the final trade values.

    Args:
        board_df (pl.DataFrame): The input player board, expected to have ECR data.
        league_id (str | None): The Sleeper league ID, used to add ownership info.
        inseason (bool, optional): Flag for future use to distinguish between dynasty and in-season logic. Defaults to False.

    Returns:
        pl.DataFrame: A DataFrame with calculated trade values and relevant player info.
    """
    # Load in fantasy football rankings
    board_columns = ['fantasypros_id', 'Player', 'pos', 'ECR']
    if board_df.is_empty():
        return pl.DataFrame()

    # Filter for dynasty rankings and relevant position
    board_df = board_df[board_columns]
    board_df = board_df.filter(pl.col('pos').is_in(['QB', 'RB', 'WR', 'TE']))

    # Add player ages
    board_df = add_ages(board_df)
    board_df = board_df.select(['fantasypros_id', 'Player', 'pos', 'Age', 'ECR'])

    # Cast ID column as a string to ensure consistent filtering with other data sources, like league rosters.
    board_df = board_df.cast({'fantasypros_id': pl.Int64()})

    # Add league ownership data
    if league_id:
        board_df = add_owners(league_id, board_df)
    else:
        # If no league_id, add placeholder Owner column.
        board_df = board_df.with_columns(pl.lit('N/A').alias('Owner'))

    values_df = add_trade_values(board_df)

    return values_df

def add_trade_values(board_df: pl.DataFrame) -> pl.DataFrame:
    """
    Calculates and adds a 'Trade Value' column based on exponential scaling of ECR.

    This method transforms the linear ECR into a non-linear value scale to better
    represent the steep drop-off in value from elite players to the rest of the pack.

    Args:
        board_df (pl.DataFrame): The player board, must contain an 'ECR' column.

    Returns:
        pl.DataFrame: The board with an added 'Trade Value' column.
    """
    if board_df.is_empty():
        return board_df

    # Invert the ECR values
    max_rank = board_df['ECR'].max()
    min_rank = board_df['ECR'].min()
    values_df = board_df.with_columns((max_rank - pl.col('ECR') + min_rank).alias('inv_ecr'))

    # Calculate raw trade values
    values_df = values_df.with_columns(pl.col('inv_ecr').pow(2.2).alias('exp_val'))

    # Normalize raw trade values to a 1-9999 scale
    max_exp_val = values_df['exp_val'].max()
    values_df = values_df.with_columns((pl.col('exp_val') / max_exp_val * 9999).round(0).alias('Trade Value'))
    values_df = values_df.cast({'Trade Value': pl.Int32})

    return values_df.select(['fantasypros_id', 'Player', 'pos', 'Age', 'Trade Value', 'Owner'])



if __name__ == '__main__':
    pl.Config(tbl_rows=-1, tbl_cols=-1)

    from src.boards import create_board
    league_id = input('Enter Sleeper platform league number (This is found in the sleeper url):')
    rank_df = create_board(league_id, draft=True, positional=False)
    trade_df = create_trade_values(rank_df, league_id, inseason=False)
    print(trade_df)

