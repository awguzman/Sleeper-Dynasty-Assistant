"""
This module is responsible for calculating and assigning trade values to players.

It takes a pre-processed player board, applies an exponential scaling algorithm
to the Expert Consensus Ranks (ECR) to generate a non-linear trade value.
"""

import polars as pl
import math

from nflreadpy import load_ff_rankings, load_player_stats


def create_trade_values(board_df: pl.DataFrame) -> pl.DataFrame:
    """
    Creates a trade value board.

    This function takes DataFrames representing a player board (typically from the dashboard's data store)
    and then calculates the final trade values.

    Args:
        board_df: The input player board, expected to have ECR data. Typically comes from the dashboard's data store.

    Returns:
        pl.DataFrame: A DataFrame with calculated trade values and relevant player info.
    """
    if board_df.is_empty():
        return pl.DataFrame()

    board_columns = ['fantasypros_id', 'Player', 'Pos', 'ECR', 'Age', 'Owner']
    board_df = board_df.select(board_columns)

    # # Load in latest dynasty ECR rankings from DynastyProcess
    # latest_url = 'https://raw.githubusercontent.com/dynastyprocess/data/master/files/values-players.csv'
    # latest_columns = ['fp_id', 'player', 'pos', 'ecr_1qb']
    # latest_df = pl.read_csv(source=latest_url, columns=latest_columns)
    # latest_df = latest_df.rename({'fp_id': 'fantasypros_id', 'player': 'Player', 'ecr_1qb': 'ECR'})

    # # Join latest ECR rankings to the player board
    # board_df = board_df.join(latest_df, on=['fantasypros_id', 'Player', 'pos'], how='left', maintain_order='right')

    # --- Define Decay Parameters ---
    # Piece 1 (ECR 1-84): Steep decay for starters.
    alpha1 = (math.log(0.2) / 84)  # Lose 80% of top value over the first 84 players (All starters for each team).

    # Piece 2 (ECR > 84): Gentler decay for bench players.
    value_at_84 = 99 * (math.e ** (alpha1 * (84 - 1)))
    alpha2 = (math.log(0.2) / 108) # Lose 80% of remaining value over the next 108 bench/flex players.


    # --- Calculate Trade Values ---
    values_df = board_df.with_columns(
        pl.when(pl.col('ECR') <= 85).then(
            # Formula for Piece 1
            99 * (math.e ** (alpha1 * (pl.col('ECR') - 1)))
        ).otherwise(
            # Formula for Piece 2
            value_at_84 * (math.e ** (alpha2 * (pl.col('ECR') - 84)))
        ).round(0).alias('Value')
    )

    values_df = values_df.cast({'Value': pl.Int64})

    return values_df.select(['fantasypros_id', 'Player', 'Pos', 'Age', 'Value', 'Owner'])