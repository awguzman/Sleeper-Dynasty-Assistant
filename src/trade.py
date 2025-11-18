"""
This module is responsible for calculating and assigning trade values to players.

It takes a pre-processed player board, applies an exponential scaling algorithm
to the Expert Consensus Ranks (ECR) to generate a non-linear trade value.
"""

import polars as pl
import math

from nflreadpy import load_ff_rankings
from src.boards import add_ages, add_owners

def create_trade_values(board_df: pl.DataFrame, inseason: bool = False) -> pl.DataFrame:
    """
    Creates a trade value board.

    This function takes a board DataFrame (typically from the dashboard's data store),
    adds data like ages and ownership, and then calculates the final trade values.

    Args:
        board_df (pl.DataFrame): The input player board, expected to have ECR data.
        inseason (bool, optional): Flag for future use to distinguish between dynasty and in-season logic. Defaults to False.

    Returns:
        pl.DataFrame: A DataFrame with calculated trade values and relevant player info.
    """
    if board_df.is_empty():
        return pl.DataFrame()

    # Add ages if not already done.
    if 'Age' not in board_df.columns:
        board_df = add_ages(board_df)

    # Filter for dynasty rankings and relevant position
    board_columns = ['fantasypros_id', 'Player', 'pos', 'Age', 'ECR', 'Owner']
    board_df = board_df[board_columns]
    board_df = board_df.filter(pl.col('pos').is_in(['QB', 'RB', 'WR', 'TE']))

    # --- Define Decay Parameters ---
    min_rank = board_df['ECR'].min()

    # Piece 1 (ECR 1-50): Steep decay for starters.
    alpha1 = (math.log(0.25) / 50)  # Lose 75% of top value over the first 50 players.

    # Piece 2 (ECR > 50): Gentler decay for bench players.
    value_at_50 = 99 * (math.e ** (alpha1 * (50 - min_rank)))
    alpha2 = (math.log(0.2) / 150) # Lose 80% of remaining value over the next 150 players.


    # --- Calculate Trade Values ---
    values_df = board_df.with_columns(
        pl.when(pl.col('ECR') <= 50).then(
            # Formula for Piece 1
            99 * (math.e ** (alpha1 * (pl.col('ECR') - min_rank)))
        ).otherwise(
            # Formula for Piece 2
            value_at_50 * (math.e ** (alpha2 * (pl.col('ECR') - 50)))
        ).round(0).alias('Value')
    )

    values_df = values_df.cast({'Value': pl.Int64})

    return values_df.select(['fantasypros_id', 'Player', 'pos', 'Age', 'Value', 'Owner'])
