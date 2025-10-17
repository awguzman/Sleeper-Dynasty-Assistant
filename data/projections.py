import pandas as pd

from data.league_info import get_scoring_weights


def compute_projected_points(pos: str, league_id: str, draft = False) -> pd.DataFrame:
    """
    Retrieve Fantasypros projected season stats for a given position and use these to calculate projected fantasy
        points for the given league scoring settings.

    Args:
        pos: Position to retrieve projected stats for. Can only be qb, rb, wr, or te.
        league_id: The unique identifier for the Sleeper league.
        draft: Boolean flag to switch between full season projections or weekly projections.

    Returns:
        proj_df: A pandas DataFrame containing one row per player, with columns giving Player and Proj. Points.
    """

    if pos not in ['qb', 'rb', 'wr', 'te']:
        raise Exception(f'Failed to retrieve Fantasypros projected season stats. '
                        f'Invalid position: {pos}. Must be qb, rb, wr, or te. ')

    # Store fantasypros url for projected stats.
    if draft:
        proj_url = f'https://www.fantasypros.com/nfl/projections/{pos}.php?week=draft'
    else:
        proj_url = f'https://www.fantasypros.com/nfl/projections/{pos}.php'

    # Scrape Fantasy Pro's projected player stats and store in a DataFrame.
    proj_df = pd.read_html(proj_url, header=1)[0]

    # Pick out columns that are important for fantasy point calculation.
    if pos == 'qb':
        stats_columns = ['Player', 'YDS', 'TDS', 'INTS', 'YDS.1', 'TDS.1', 'FL']
    elif pos == 'rb':
        stats_columns = ['Player', 'YDS', 'TDS', 'REC', 'YDS.1', 'TDS.1', 'FL']
    elif pos == 'wr':
        stats_columns = ['Player', 'REC', 'YDS', 'TDS', 'YDS.1', 'TDS.1', 'FL']
    else:
        stats_columns = ['Player', 'REC', 'YDS', 'TDS', 'FL']

    # Filter columns according to the columns picked out above.
    proj_df = proj_df[stats_columns]

    # Compute projected fantasy points and add a column in the positional DataFrames.
    scoring_weights = get_scoring_weights(league_id)

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

    # Filter out raw projected stats.
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