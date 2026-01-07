"""
This module provides functions for calculating and retrieving advanced player/team statistics.
"""

import polars as pl

from nflreadpy import get_current_season, get_current_week, load_nextgen_stats, load_player_stats, load_ff_opportunity
from src.boards import add_owners

def compute_efficiency(league_df: pl.DataFrame | None) -> pl.DataFrame:
    """
    Computes player fantasy production efficiency data

    This function loads player opportunity data, filters it, and aggregates it based on
    whether the analysis is being performed during season.

    Args:
        league_df (str, optional): Sleeper League data for ownership filtering.

    Returns:
        pl.DataFrame: A DataFrame containing player efficiency metrics.
    """
    season = get_current_season(roster=True) # This updates right before the start of week 1.
    opp_features = ['season', 'week', 'player_id', 'full_name', 'position', 'total_fantasy_points', 'total_fantasy_points_exp']

    # Load player opportunity data for the selected season.
    opp_df = load_ff_opportunity(seasons=[season], stat_type='weekly', model_version='latest')
    opp_df = opp_df.select(opp_features)

    # Group by player and sum the points over all weeks of the season.
    opp_df = opp_df.group_by(['season', 'player_id', 'full_name', 'position']).agg([
        pl.col('total_fantasy_points').sum(),
        pl.col('total_fantasy_points_exp').sum()
    ]).filter(pl.col('total_fantasy_points') >= get_current_week())  # Limit low participation players

    # Compute efficiency as difference between actual and expected points.
    opp_df = opp_df.with_columns((pl.col('total_fantasy_points_exp') - pl.col('total_fantasy_points')).round(2).alias('Efficiency'))

    opp_df = opp_df.rename({'player_id': 'gsis_id',
                            'full_name': 'Player',
                            'position': 'pos',
                            'total_fantasy_points': 'Actual Points',
                            'total_fantasy_points_exp': 'Expected Points'
                            })

    opp_df = add_owners(league_df, opp_df)

    return opp_df


def receiving_share(league_df: pl.DataFrame | None) -> pl.DataFrame:
    """
    Retrieves receiving share metrics for receivers along with production metrics.

    This function loads player-level season stats, filters for receivers (WR + TE),
    and adds league ownership information if a league_id is provided.

    Args:
        league_df: The Sleeper league data used to add ownership info.
                                If None, ownership data will not be added.

    Returns:
        pl.DataFrame: A DataFrame containing receiving share data for wide receivers.
    """
    share_features = ['player_id', 'player_display_name', 'position', 'target_share', 'air_yards_share', 'wopr']
    prod_features = ['player_id', 'rec_yards_gained', 'rec_yards_gained_team']

    # Load player-level season stats for the current regular season.
    share_df = load_player_stats(seasons=get_current_season(), summary_level='reg')
    share_df = share_df.select(share_features)
    share_df = share_df.filter(pl.col('position').is_in(['WR', 'TE'])).drop('position')
    share_df = share_df.rename({'player_id': 'gsis_id',
                                'player_display_name': 'Player',
                                'target_share': 'Target Share',
                                'air_yards_share': 'Air Yards Share',
                                'wopr': 'WOPR'
                                })

    # Load player/team-level stats for receiving yards gained.
    prod_df = load_ff_opportunity(seasons=get_current_season(), stat_type='weekly')
    prod_df = prod_df.select(prod_features).rename({'player_id': 'gsis_id'})
    prod_df = prod_df.group_by(['gsis_id']).agg([
        pl.col('rec_yards_gained').sum(),
        pl.col('rec_yards_gained_team').sum()]
    )
    prod_df = prod_df.with_columns((pl.col('rec_yards_gained') / pl.col('rec_yards_gained_team')).round(3).alias('Receiving Yard Share'))
    prod_df = prod_df.drop('rec_yards_gained', 'rec_yards_gained_team')
    share_df = share_df.join(prod_df, on='gsis_id', how='left')

    # Add ownership information if a league_df is provided.
    share_df = add_owners(league_df, share_df)

    return share_df

def rushing_share(league_df: pl.DataFrame | None) -> pl.DataFrame:
    """
        Retrieves rushing share metrics for running backs along with production metrics.

        This function loads player-level season stats, filters for running backs,
        and adds league ownership information if a league_id is provided.

        Args:
            league_df: The Sleeper league data used to add ownership info.
                                    If None, ownership data will not be added.

        Returns:
            pl.DataFrame: A DataFrame containing receiving share data for wide receivers.
        """
    # Load player-level season rushing stats.
    share_features = ['player_id', 'full_name', 'position', 'rush_attempt', 'rush_attempt_team', 'rush_yards_gained', 'rush_yards_gained_team']
    share_df = load_ff_opportunity(seasons=get_current_season(), stat_type='weekly')
    share_df = share_df.select(share_features).filter(pl.col('position') == 'RB')
    share_df = share_df.group_by(['player_id', 'full_name']).agg([
        pl.col('rush_attempt').sum(),
        pl.col('rush_attempt_team').sum(),
        pl.col('rush_yards_gained').sum(),
        pl.col('rush_yards_gained_team').sum()
    ])

    share_df = share_df.with_columns(
        (pl.col('rush_attempt') / pl.col('rush_attempt_team')).round(3).alias('Rushing Attempt Share'),
        (pl.col('rush_yards_gained') / pl.col('rush_yards_gained_team')).round(3).alias('Rushing Yard Share')
    )

    share_df = share_df.rename({'player_id': 'gsis_id', 'full_name': 'Player'})

    # Add ownership information if a league_df is provided.
    share_df = add_owners(league_df, share_df)

    return share_df

def qb_yac_dependence(league_df: pl.DataFrame | None) -> pl.DataFrame:
    

    return dep_df

