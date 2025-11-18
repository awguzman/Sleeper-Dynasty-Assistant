"""
This module provides functions for calculating and retrieving advanced player/team statistics.
"""

import polars as pl

from nflreadpy import get_current_season, load_nextgen_stats, load_player_stats
from src.boards import add_owners

def receiving_share(league_df: pl.DataFrame | None) -> pl.DataFrame:
    """
    Retrieves receiving share metrics (Target Share, Air Yards Share, WOPR) for wide receivers.

    This function loads player-level season stats, filters for wide receivers,
    and adds league ownership information if a league_id is provided.

    Args:
        league_df: The Sleeper league data used to add ownership info.
                                If None, ownership data will not be added.

    Returns:
        pl.DataFrame: A DataFrame containing receiving share data for wide receivers.
    """
    share_features = ['player_id', 'player_display_name', 'position', 'target_share', 'air_yards_share', 'wopr']

    # Load player-level season stats for the current regular season.
    share_df = load_player_stats(seasons=get_current_season(), summary_level='reg')
    
    share_df = share_df.select(share_features)
    share_df = share_df.filter(pl.col('position').is_in(['WR', 'TE'])).drop('position')

    share_df = share_df.rename({'player_id': 'gsis_id', 'player_display_name': 'Player', 'target_share': 'Target Share',
                                'air_yards_share': 'Air Yards Share', 'wopr': 'WOPR'})

    # Add ownership information if a league_df is provided.
    share_df = add_owners(league_df, share_df)

    return share_df


def stacked_box_efficiency(league_df: pl.DataFrame | None) -> pl.DataFrame:
    """
    Retrieves rushing efficiency data vs stacked boxes (8 or more players)

    This function loads player-level season stats,
    and adds league ownership information if a league_id is provided.

    Args:
        league_df: The Sleeper league ID, used to add ownership info.
                                If None, ownership data will not be added.

    Returns:
        pl.DataFrame: A DataFrame containing stacked box efficiency data for running backs.
    """

    box_features = ['week', 'player_gsis_id', 'player_display_name', 'player_position', 'percent_attempts_gte_eight_defenders', 'rush_yards_over_expected_per_att', 'rush_attempts']

    box_df = load_nextgen_stats(seasons=get_current_season(), stat_type='rushing')
    box_df = box_df.select(box_features)
    box_df = box_df.filter(~(pl.col('rush_attempts') == 0))

    box_df = box_df.group_by(['player_gsis_id', 'player_display_name']).agg([
        pl.col('percent_attempts_gte_eight_defenders').mean().round(2),
        pl.col('rush_yards_over_expected_per_att').mean().round(2),
        pl.col('rush_attempts').sum()
    ])

    box_df = box_df.rename({'player_gsis_id': 'gsis_id', 'player_display_name': 'Player',
                            'percent_attempts_gte_eight_defenders': 'Stacked Box Percentage',
                            'rush_yards_over_expected_per_att': 'Rush Yards over Expected per Attempt',
                            'rush_attempts': 'Rush Attempts'})

    box_df = add_owners(league_df, box_df)

    return box_df


def receiver_separation(league_df: pl.DataFrame | None) -> pl.DataFrame:
    """
    Retrieves receiver separation vs. cushion data from Next Gen Stats.

    Args:
        league_df: The Sleeper league data used to add ownership info.

    Returns:
        pl.DataFrame: A DataFrame containing separation and cushion data for receivers.
    """
    # Load Next Gen Stats for receiving
    separation_df = load_nextgen_stats(seasons=get_current_season(), stat_type='receiving')

    # Define and select the necessary features
    sep_features = ['week', 'player_gsis_id', 'player_display_name', 'player_position','avg_cushion', 'avg_separation', 'targets']
    separation_df = separation_df.select(sep_features)
    separation_df = separation_df.filter(pl.col('player_position') == 'WR').drop('player_position')

    separation_df = separation_df.group_by(['player_gsis_id', 'player_display_name']).agg([
        pl.col('avg_cushion').mean().round(2),
        pl.col('avg_separation').mean().round(2),
        pl.col('targets').sum()
    ])

    # Rename columns for consistency and readability
    separation_df = separation_df.rename({
        'player_gsis_id': 'gsis_id',
        'player_display_name': 'Player',
        'avg_cushion': 'Cushion',
        'avg_separation': 'Separation'
    })

    # Add ownership information
    separation_df = add_owners(league_df, separation_df)

    return separation_df


def qb_aggressiveness(league_df: pl.DataFrame | None) -> pl.DataFrame:
    """
    Retrieves QB playstyle data (aggressiveness vs. efficiency) from Next Gen Stats.

    Args:
        league_df: The Sleeper league data used to add ownership info.

    Returns:
        pl.DataFrame: A DataFrame containing QB playstyle data.
    """
    # Load season-level Next Gen Stats for passing
    passing_df = load_nextgen_stats(seasons=get_current_season(), stat_type='passing')

    # Define and select the necessary features
    features = [
        'week', 'player_gsis_id', 'player_display_name', 'player_position', 'aggressiveness',
        'completion_percentage_above_expectation', 'attempts'
    ]
    passing_df = passing_df.select(features)
    passing_df = passing_df.filter(pl.col('player_position') == 'QB').drop('player_position')
    passing_df = passing_df.group_by(['player_gsis_id', 'player_display_name']).agg([
        (pl.col('aggressiveness')).mean().round(2),
        pl.col('completion_percentage_above_expectation').mean().round(2),
        pl.col('attempts').sum()
    ])

    # Rename columns for consistency and readability
    passing_df = passing_df.rename({
        'player_gsis_id': 'gsis_id',
        'player_display_name': 'Player',
        'aggressiveness': 'Aggressiveness',
        'completion_percentage_above_expectation': 'CPOE'
    })

    # Add ownership information
    passing_df = add_owners(league_df, passing_df)

    return passing_df
