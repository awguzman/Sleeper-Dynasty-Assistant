"""
This module contains functions for creating visualizations for the dashboard.
"""

import polars as pl
import plotly.graph_objects as go
import plotly.express as px


def create_tier_chart(board_df: pl.DataFrame) -> go.Figure:
    """
    Creates an interactive tier chart showing player ECR with best/worst error bars.

    Args:
        board_df (pl.DataFrame): A DataFrame containing player data with tiers,
                                 ECR, Best, and Worst columns.

    Returns:
        go.Figure: A Plotly figure object ready to be displayed in a dcc.Graph.
    """
    if board_df.is_empty():
        # Return an empty figure if there's no data
        return go.Figure()

    # Calculate a dynamic height for the chart to prevent it from being squished.
    # We allocate a certain number of pixels per player.
    chart_height = board_df.height * 20

    # Prepare data for plotting
    # Ensure data is sorted and add a 'Rank' column for the y-axis
    board_df = board_df.sort('ECR').with_row_index(name="Rank", offset=1)

    # Calculate asymmetric error bar values
    # The length of the bar to the right (Worst) and left (Best) of the ECR point
    board_df = board_df.with_columns([
        (pl.col('Worst') - pl.col('ECR')).alias('error_plus'),
        (pl.col('ECR') - pl.col('Best')).alias('error_minus')
    ])

    # Prepend "Tier: " to the Tier column for a more descriptive legend.
    # Casting to string also ensures Plotly uses a discrete (not gradient) color scale.
    board_df = board_df.with_columns((pl.lit("Tier: ") + pl.col('Tier').cast(pl.String)).alias('Tier'))


    # Create the plot using Plotly Express for its simplicity with colors and error bars.
    fig = px.scatter(
        board_df.to_pandas(),
        x='ECR',
        y='Rank',
        color='Tier',
        color_discrete_sequence=px.colors.qualitative.Dark24,
        custom_data=['Player', 'Best', 'Worst', 'Tier', 'Confidence'],  # Data to show on hover
        error_x='error_plus',
        error_x_minus='error_minus'
    )

    # Customize the figure's layout.
    fig.update_layout(
        height=chart_height,
        title="Player Positional Ranking Tiers",
        xaxis_title="Expert Consensus Rank (ECR)",
        yaxis_title="Positional Rank",
        yaxis_autorange="reversed",  # Puts Rank 1 at the top
        legend_title_text='Legend',
        # Add a right margin to give the text labels some space
        margin=dict(r=120)
    )

    # Create a mapping from tier name to its assigned color from the figure's traces
    tier_color_map = {trace.name: trace.marker.color for trace in fig.data}

    # Add player names as annotations to the right of the 'Worst' ECR value
    for i, row in enumerate(board_df.iter_rows(named=True)):
        fig.add_annotation(
            x=row['Worst'],  # Position text at the end of the error bar
            y=row['Rank'],
            text=row['Player'],
            showarrow=False,
            xanchor='left',  # Anchor text to the left
            xshift=5,        # Add a small 5px shift for padding
            yanchor='middle',  # Use the color mapped to the player's tier
            font=dict(size=10, color=tier_color_map.get(row['Tier'], 'lightgrey'))
        )

    # Customize the hover text for a informative tooltip.
    fig.update_traces(
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>" +
            "Rank: %{y}<br>" +
            "ECR: %{x}<br>" +
            "Best: %{customdata[1]} | Worst: %{customdata[2]}<br>" +
            "%{customdata[3]}<br>" +
            "Confidence: %{customdata[4]}" +
            "<extra></extra>"  # Hides the secondary box
        )
    )

    return fig

if __name__ == '__main__':
    pl.Config(tbl_rows=-1, tbl_cols=-1)

    from src.boards import create_board
    from src.tiers import create_tiers
    board_df = create_board(draft=True).filter(pl.col('pos') == 'WR')
    board_df = create_tiers(board_df, tier_range=range(10,12+1), n_players=60)
    print(create_tier_chart(board_df).show())