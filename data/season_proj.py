import pandas as pd
import requests


def compute_projected_points(pos: str, league_id: str) -> pd.DataFrame:
    """ Scrape Fantasypros.com projected stats for fantasy point calculations. """

    if pos not in ['qb', 'rb', 'wr', 'te']:
        raise Exception(f'Failed to retrieve Fantasypros projected season stats. '
                        f'Invalid position: {pos}. Must be qb, rb, wr, or te. ')

    # Store fantasypros url for projected stats.
    proj_url = f'https://www.fantasypros.com/nfl/projections/{pos}.php?week=draft'

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

def get_scoring_weights(league_id: str) -> dict:

    sleeper_url = f'https://api.sleeper.app/v1/league/{league_id}'

    sleeper_request = requests.get(sleeper_url).json()
    scoring_weights = sleeper_request['scoring_settings']

    return scoring_weights

if __name__ == '__main__':
    # For debugging: prevent pandas from truncating display
    pd.set_option('display.max_rows', None)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)

    league_id = input('Enter Sleeper platform league number (This is found in the sleeper url):')
    qb_df = compute_projected_points('qb', league_id)
    rb_df = compute_projected_points('rb', league_id)
    wr_df = compute_projected_points('wr', league_id)
    te_df = compute_projected_points('te', league_id)

    print(rb_df)