"""
This module handles the scraping and calculation of player fantasy point projections.

It fetches raw statistical projections from FantasyPros for either a full season (draft)
or a single week, then applies a given league's scoring settings to calculate
a final projected fantasy point total for each player.
"""
import pandas as pd

from data.league_info import get_scoring_weights


def compute_projected_points(pos: str, league_id: str, draft: bool = False) -> pd.DataFrame:
    """
    Scrapes FantasyPros for player projections and calculates fantasy points.

    Args:
        pos (str): The position to retrieve stats for (e.g., 'qb', 'rb', 'wr', 'te').
        league_id (str): The unique identifier for the Sleeper league, used for scoring rules.
        draft (bool, optional): If True, fetches full-season "draft" projections.
                                If False, fetches current week projections. Defaults to False.

    Returns:
        pd.DataFrame: A DataFrame with columns for 'Player' and 'Proj. Points'.
    """

    if pos not in ['qb', 'rb', 'wr', 'te']:
        raise Exception(f'Failed to retrieve Fantasypros projected season stats. '
                        f'Invalid position: {pos}. Must be qb, rb, wr, or te. ')

    # Construct the correct FantasyPros URL based on whether we need season or weekly projections.
    if draft:
        proj_url = f'https://www.fantasypros.com/nfl/projections/{pos}.php?week=draft'
    else:
        proj_url = f'https://www.fantasypros.com/nfl/projections/{pos}.php'

    # Use pandas' read_html to directly scrape the main data table from the URL.
    proj_df = pd.read_html(proj_url, header=1)[0]

    # Define the relevant stat columns for each position.
    # Note: FantasyPros uses ambiguous column names (e.g., YDS, YDS.1) that change meaning by position.
    if pos == 'qb':
        # For QBs: YDS is Passing Yards, YDS.1 is Rushing Yards.
        stats_columns = ['Player', 'YDS', 'TDS', 'INTS', 'YDS.1', 'TDS.1', 'FL']
    elif pos == 'rb':
        # For RBs: YDS is Rushing Yards, YDS.1 is Receiving Yards.
        stats_columns = ['Player', 'YDS', 'TDS', 'REC', 'YDS.1', 'TDS.1', 'FL']
    elif pos == 'wr':
        # For WRs: YDS is Receiving Yards, YDS.1 is Rushing Yards.
        stats_columns = ['Player', 'REC', 'YDS', 'TDS', 'YDS.1', 'TDS.1', 'FL']
    else:
        # For TEs: YDS is Receiving Yards.
        stats_columns = ['Player', 'REC', 'YDS', 'TDS', 'FL']

    # Filter columns according to the columns picked out above.
    proj_df = proj_df[stats_columns]

    # Compute projected fantasy points and add a column in the positional DataFrames.
    scoring_weights = get_scoring_weights(league_id)

    # Calculate 'Proj. Points' by applying the league's scoring weights to the scraped stats.
    if pos == 'qb':
        proj_df['Proj. Points'] = (
                proj_df['YDS'] * scoring_weights['pass_yd'] +
                proj_df['TDS'] * scoring_weights['pass_td'] +
                proj_df['INTS'] * scoring_weights['pass_int'] +
                proj_df['YDS.1'] * scoring_weights['rush_yd'] +
                proj_df['TDS.1'] * scoring_weights['rush_td'] +
                proj_df['FL'] * scoring_weights['fum_lost']).round(2)

    elif pos == 'rb':
        proj_df['Proj. Points'] = (
                proj_df['YDS'] * scoring_weights['rush_yd'] +
                proj_df['TDS'] * scoring_weights['rush_td'] +
                proj_df['REC'] * scoring_weights['rec'] +
                proj_df['YDS.1'] * scoring_weights['rec_yd'] +
                proj_df['TDS.1'] * scoring_weights['rec_td'] +
                proj_df['FL'] * scoring_weights['fum_lost']).round(2)

    elif pos == 'wr':
        proj_df['Proj. Points'] = (
                proj_df['REC'] * scoring_weights['rec'] +
                proj_df['YDS'] * scoring_weights['rec_yd'] +
                proj_df['TDS'] * scoring_weights['rec_td'] +
                proj_df['YDS.1'] * scoring_weights['rush_yd'] +
                proj_df['TDS.1'] * scoring_weights['rush_td'] +
                proj_df['FL'] * scoring_weights['fum_lost']).round(2)

    else:
        proj_df['Proj. Points'] = (
                proj_df['REC'] * scoring_weights['rec'] +
                proj_df['YDS'] * scoring_weights['rec_yd'] +
                proj_df['TDS'] * scoring_weights['rec_td'] +
                proj_df['FL'] * scoring_weights['fum_lost']).round(2)

    # Return only the player's name and their calculated projected points.
    proj_df = proj_df[['Player', 'Proj. Points']]

    return proj_df

if __name__ == '__main__':
    # For debugging: prevent pandas from truncating display
    pd.set_option('display.max_rows', None)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)

    league_id = input('Enter Sleeper platform league number (This is found in the sleeper url):')
    rb_df = compute_projected_points('rb', league_id, draft=False)

    print(rb_df)