"""
This module provides player tiering functionality via model-based clustering.

It takes a DataFrame of players stats and ECR rankings, applies a Gaussian Mixture model
to group them into tiers and returns the DataFrame with an added 'Tier' column.
"""

import polars as pl
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler

def create_tiers(board_df: pl.DataFrame, tier_range: range, n_players: int) -> pl.DataFrame:
    board_df = board_df.head(n_players)
    features = ['ECR', 'Best', 'Worst']
    cluster_df = board_df.select(features).to_numpy()

    scaler = StandardScaler()
    scaled_data = scaler.fit_transform(cluster_df)

    # Use Bayesian Information Criterion (BIC) to find the optimal number of tiers.
    bic_scores = [
        GaussianMixture(n_components=n, random_state=13, n_init=5).fit(scaled_data).bic(scaled_data)
        for n in tier_range
    ]
    # Find the number of components that gives the lowest BIC score
    optimal_n = tier_range[bic_scores.index(min(bic_scores))]
    # print(f"Optimal number of tiers found: {optimal_n}")
    n_tiers = optimal_n

    gmm = GaussianMixture(n_components=n_tiers, n_init=10, random_state=13)
    tier_labels = gmm.fit_predict(scaled_data)
    probs = gmm.predict_proba(scaled_data)

    board_df = board_df.with_columns([
        pl.Series('Tier', tier_labels),
        pl.Series('Confidence', [f'{p.max()*100:.2f}%' for p in probs])
    ])

    tier_order = board_df.group_by('Tier').agg(pl.col('ECR').mean()).sort('ECR')
    tier_map = {row['Tier']:i + 1 for i, row in enumerate(tier_order.iter_rows(named=True))}
    board_df = board_df.with_columns(pl.col('Tier').replace(tier_map))

    return board_df.select(['Player', 'ECR', 'Best', 'Worst', 'Std', 'Tier', 'Confidence'])

if __name__ == '__main__':
    pl.Config(tbl_rows=-1, tbl_cols=-1)

    from src.boards import create_board
    board_df = create_board(draft=True).filter(pl.col('pos') == 'RB')
    board_df = create_tiers(board_df, tier_range=range(5, 10 + 1), n_players=40)
    print(board_df)