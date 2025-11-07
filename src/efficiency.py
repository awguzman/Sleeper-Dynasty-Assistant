
"""
This module provides functions to compute player efficiency metrics based on opportunity data.
"""

import polars as pl
from nflreadpy import load_ff_opportunity, get_current_season, get_current_week
from src.boards import add_owners

def compute_efficiency(league_id: str | None, offseason: bool = False) -> pl.DataFrame:
    """
    Computes player efficiency data, either for the full season (offseason) or the previous week (in-season).

    This function loads player opportunity data, filters it, and aggregates it based on
    whether the analysis is being performed during the offseason or in-season.

    Args:
        league_id (str, optional): Sleeper League ID for ownership filtering.
        offseason (bool, optional): If True, aggregates data for the entire previous season.
                                    If False, filters data for the previous week only. Defaults to False.

    Returns:
        pl.DataFrame: A DataFrame containing player efficiency metrics.
    """
    current_season = get_current_season(roster=False) # This updates on March 15 (Start of Free Agency).
    opp_features = ['season', 'week', 'player_id', 'full_name', 'position', 'total_fantasy_points', 'total_fantasy_points_exp']

    if offseason:
        # Load player opportunity data for the previous season.
        opp_df = load_ff_opportunity(seasons=[current_season - 1], stat_type='weekly', model_version='latest')
        opp_df = opp_df.select(opp_features)

        # Group by player and sum the points over all weeks of the season.
        opp_df = opp_df.group_by(['season', 'player_id', 'full_name', 'position']).agg([
            pl.col('total_fantasy_points').sum(),
            pl.col('total_fantasy_points_exp').sum()
        ]).filter(pl.col('total_fantasy_points') > 25) # Limit low participation players
    else:
        # Load player opportunity data for the current season.
        opp_df = load_ff_opportunity(seasons=[current_season], stat_type='weekly', model_version='latest')
        opp_df = opp_df.select(opp_features).filter(pl.col('total_fantasy_points') > 1)

        # If in-season, just look at the previous week.
        prev_week = get_current_week() - 1 # This updates after MNF
        opp_df = opp_df.filter(pl.col('week') == prev_week)

    # Compute efficiency as difference between actual and expected points.
    opp_df = opp_df.with_columns((pl.col('total_fantasy_points_exp') - pl.col('total_fantasy_points')).round(2).alias('Efficiency'))

    opp_df = opp_df.rename({'player_id': 'gsis_id', 'full_name': 'Player', 'position': 'pos', 'total_fantasy_points': 'Actual Points', 'total_fantasy_points_exp': 'Expected Points'})

    opp_df = add_owners(league_id, opp_df)

    return opp_df

if __name__ == '__main__':
    # This block is for standalone testing and debugging of this module.
    league_id = input('Enter Sleeper platform league number (This is found in the sleeper url):')
    opp_df = compute_efficiency(league_id=None, offseason=True)
    print(opp_df)
