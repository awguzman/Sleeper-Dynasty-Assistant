"""
This module provides functions for analyzing team rosters and strengths.
"""

import polars as pl
from src.trade import create_trade_values

def analyze_team(board_df: pl.DataFrame, owner_name: str) -> tuple[pl.DataFrame, pl.DataFrame, int]:
    """
    Analyzes a specific owner's team, returning their roster and positional strength rankings.

    Args:
        board_df (pl.DataFrame): The player board with ECR data.
        owner_name (str): The name of the owner to analyze.

    Returns:
        tuple[pl.DataFrame, pl.DataFrame, int]:
            - user_roster: DataFrame of the user's players with trade values, sorted by position and value.
            - user_ranks: DataFrame of the user's positional ranks and total values compared to the league.
            - league_size: The number of teams in the league (excluding Free Agents).
    """
    # Calculate trade values for the entire board
    values_df = create_trade_values(board_df)

    # 1. Get User's Roster
    # Filter for the specific user and sort for display
    user_roster = values_df.filter(pl.col('Owner') == owner_name)
    user_roster = user_roster.sort(['Pos', 'Value'], descending=[False, True])

    # 2. Calculate League-Wide Positional Strengths
    # Filter out Free Agents for ranking purposes
    league_teams_df = values_df.filter(pl.col('Owner') != 'Free Agent')

    # Group by Owner and Position to get total value
    pos_strengths = league_teams_df.group_by(['Owner', 'Pos']).agg(
        pl.col('Value').sum().alias('Total Value')
    )

    # Rank owners within each position
    pos_strengths = pos_strengths.with_columns(pl.col('Total Value').rank(descending=True).over('Pos').alias('Rank'))

    # Calculate Overall Strength (Sum of all positions)
    overall_strength = league_teams_df.group_by('Owner').agg(pl.col('Value').sum().alias('Total Value')).with_columns([
        pl.lit('Overall').alias('Pos'),
        pl.col('Total Value').rank(descending=True).alias('Rank')
    ])
    
    # Calculate positional and overall averages
    pos_averages = pos_strengths.group_by('Pos').agg(
        pl.col('Total Value').mean().round(0).alias('Avg Value')
    )
    overall_average = overall_strength.select(
        pl.lit('Overall').alias('Pos'),
        pl.col('Total Value').mean().round(0).alias('Avg Value')
    )
    all_averages = pl.concat([pos_averages, overall_average])

    # Store the number of teams in the league
    league_size = overall_strength.height

    # Combine positional and overall strengths
    cols = ['Owner', 'Pos', 'Total Value', 'Rank']
    all_strengths = pl.concat([pos_strengths.select(cols), overall_strength.select(cols)])
    all_strengths = all_strengths.join(all_averages, on='Pos', how='left')

    # Filter for the specific user's ranks
    user_ranks = all_strengths.filter(pl.col('Owner') == owner_name)

    return user_roster, user_ranks, league_size