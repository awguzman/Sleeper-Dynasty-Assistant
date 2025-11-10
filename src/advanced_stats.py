
import polars as pl

from nflreadpy import get_current_season, load_nextgen_stats, load_player_stats
from src.boards import add_owners

def receiving_share(league_id: str | None,) -> pl.DataFrame:

    share_features = ['player_id', 'player_display_name', 'position', 'target_share', 'air_yards_share', 'wopr']

    # Load player level season stats.
    share_df = load_player_stats(seasons=get_current_season(), summary_level='reg')
    share_df = share_df.select(share_features)
    share_df = share_df.filter(pl.col('position') == 'WR').drop('position')

    # Reformat columns
    share_df = share_df.rename({'player_id': 'gsis_id', 'player_display_name': 'Player', 'target_share': 'Target Share',
                                'air_yards_share': 'Air Yards Share', 'wopr': 'WOPR'})

    # Add owners if league_id is available
    share_df = add_owners(league_id, share_df)

    return share_df

if __name__ == '__main__':
    print(receiving_share(league_id = None))