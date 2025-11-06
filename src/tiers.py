"""
This module provides player tiering functionality via model-based clustering.

It takes a DataFrame of player stats and ECR rankings, applies a Gaussian Mixture
Model (GMM) to group them into tiers, and returns the DataFrame with an added
'Tier' and 'Confidence' column.
"""

import polars as pl
from sklearn.mixture import GaussianMixture
from sklearn.preprocessing import StandardScaler

def create_tiers(board_df: pl.DataFrame, tier_range: range, n_players: int) -> pl.DataFrame:
    """
    Applies a Gaussian Mixture Model (GMM) to cluster players into tiers.

    It determines the optimal number of tiers within a given range by finding
    the model with the lowest Bayesian Information Criterion (BIC) score.

    Args:
        board_df (pl.DataFrame): The input DataFrame containing player data.
        tier_range (range): A range of potential tier counts to test (e.g., range(8, 15)).
        n_players (int): The number of top players from the board to consider for tiering.

    Returns:
        pl.DataFrame: A new DataFrame containing the tiered players with relevant columns.
    """
    # Prepare data for clustering
    board_df = board_df.head(n_players)
    features = ['ECR', 'Best', 'Worst']
    # Convert to NumPy array for scikit-learn compatibility.
    cluster_df = board_df.select(features).to_numpy()

    # Scale the features to ensure they are weighted equally by the model.
    scaler = StandardScaler()
    scaled_data = scaler.fit_transform(cluster_df)

    # Use Bayesian Information Criterion (BIC) to find the optimal number of tiers.
    # This loop tests each number of tiers in the provided range and finds the one
    # that best fits the data without being overly complex.
    bic_scores = [
        GaussianMixture(n_components=n, random_state=13, n_init=5).fit(scaled_data).bic(scaled_data)
        for n in tier_range
    ]
    # Find the number of components that gives the lowest BIC score.
    optimal_n = tier_range[bic_scores.index(min(bic_scores))]
    n_tiers = optimal_n

    # Apply the GMM with the chosen number of tiers.
    gmm = GaussianMixture(n_components=n_tiers, n_init=10, random_state=13)
    tier_labels = gmm.fit_predict(scaled_data)
    probs = gmm.predict_proba(scaled_data)

    # Add the results back to the Polars DataFrame.
    board_df = board_df.with_columns([
        pl.Series('Tier', tier_labels),
        pl.Series('Confidence', [f'{p.max()*100:.2f}%' for p in probs])
    ])

    # Order the tiers logically (GMM labels are arbitrary).
    # We calculate the average ECR for each tier and sort by that to get the true order.
    tier_order = board_df.group_by('Tier').agg(pl.col('ECR').mean()).sort('ECR')
    tier_map = {row['Tier']:i + 1 for i, row in enumerate(tier_order.iter_rows(named=True))}
    board_df = board_df.with_columns(pl.col('Tier').replace(tier_map))

    # Return a final DataFrame with a clean selection of columns for display.
    return board_df.select(['Player', 'ECR', 'Best', 'Worst', 'Std', 'Tier', 'Confidence', 'Owner'])

if __name__ == '__main__':
    pl.Config(tbl_rows=-1, tbl_cols=-1)

    from src.boards import create_board
    board_df = create_board(draft=True).filter(pl.col('pos') == 'RB')
    board_df = create_tiers(board_df, tier_range=range(5, 10 + 1), n_players=40)
    print(board_df)