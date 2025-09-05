import pandas as pd
import requests
import re
import json


def get_adp(pos: str) -> pd.DataFrame:
    """
    Get Fantasypros ADP Data for the given position.

    Args:
        pos: Position to retrieve ADP data for. Can only be qb, rb, wr, or te.

    Returns:
        A pandas DataFrame containing one row per player, with columns giving fantasypros_id, Player, Age, Position Rank,
        ECR Min, ECR Max, ADP, and ECR Std.
    """

    if pos not in ['qb', 'rb', 'wr', 'te']:
        raise Exception(f'Dynasty ADP data failed. Invalid position: {pos}. Must be qb, rb, wr, or te. ')

    adp_url = f'https://www.fantasypros.com/nfl/rankings/dynasty-{pos}.php'

    # Find the ecrData .JSON and Load it in as a DataFrame.
    adp_response = requests.get(adp_url)
    adp_match = re.search(r'var ecrData = (\{.*?\});', adp_response.text)
    if not adp_match:
        raise Exception(f'Cannot find ADP data in {adp_url}.')

    adp_json = adp_match.group(1)
    adp_data = json.loads(adp_json)
    players_list = (adp_data.get('players', []))
    adp_df = pd.DataFrame(players_list)

    adp_df['Player (Team)'] = adp_df['player_name'] + ' ' + adp_df['player_team_id']
    adp_columns = ['player_id', 'Player', 'player_age', 'pos_rank', 'rank_min', 'rank_max', 'rank_ave', 'rank_std']
    adp_df = adp_df[adp_columns]
    adp_df = adp_df.rename({'player_id': 'fantasypros_id',
                            'player_age': 'Age',
                            'pos_rank': 'Pos. Rank',
                            'rank_min': 'ECR Min',
                            'rank_max': 'ECR Max',
                            'rank_ave': 'ADP',
                            'rank_std': 'ECR Std'}, axis=1)

    return adp_df


if __name__ == '__main__':
    # For debugging: prevent pandas from truncating display
    pd.set_option('display.max_rows', None)
    pd.set_option('display.max_columns', None)
    pd.set_option('display.width', None)

    adp_df = get_adp('qb')
    print(adp_df)