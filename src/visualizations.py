"""
This module contains functions for creating visualizations for the dashboard.
"""

import polars as pl
import plotly.graph_objects as go
import plotly.express as px


def create_tier_chart(board_df: pl.DataFrame, user_name: str | None) -> go.Figure:
    """
    Creates an interactive tier chart showing player ECR with best/worst error bars.

    Args:
        board_df (pl.DataFrame): A DataFrame containing player data with tiers,
                                 ECR, Best, and Worst columns.
        user_name (str, Optional): Username for conditional styling of owned players.

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

    # Casting to string also ensures Plotly uses a discrete color scale.
    board_df = board_df.with_columns((pl.lit("Tier: ") + pl.col('Tier').cast(pl.String)).alias('Tier'))

    # Create the plot.
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

    # Add player names as annotations to the right of the 'Worst' ECR value and stylize owned players.
    for i, row in enumerate(board_df.iter_rows(named=True)):
        fig.add_annotation(
            x=row['Worst'],  # Position text at the end of the error bar
            y=row['Rank'],
            text = f"<b>{row['Player']}</b>" if user_name and row['Owner'] == user_name and row['Owner'] == user_name else row['Player'],
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


def create_efficiency_chart(efficiency_df: pl.DataFrame, user_name: str | None = None) -> go.Figure:
    """
    Creates an interactive scatter plot showing player efficiency (actual vs. expected fantasy points).

    Args:
        efficiency_df (pl.DataFrame): A DataFrame containing player efficiency data,
                                      including 'total_fantasy_points_exp' and 'total_fantasy_points'.
        user_name (str, optional): The name of the user to highlight. Players owned by this user will be labeled. Defaults to None.

    Returns:
        go.Figure: A Plotly figure object ready to be displayed in a dcc.Graph.
    """
    if efficiency_df.is_empty():
        # Return an empty figure if there's no data
        return go.Figure()

    # Add an ownership status column for dynamic coloring
    if user_name and 'Owner' in efficiency_df.columns:
        efficiency_df = efficiency_df.with_columns(
            pl.when(pl.col('Owner') == user_name).then(
                pl.lit(user_name)
            ).when(
                pl.col('Owner') == 'Free Agent'
            ).then(pl.lit('Free Agent')
            ).otherwise(
                pl.lit('Owned by Other')
            ).alias('Status')
        )
        color_map = {user_name: '#1100FF', 'Free Agent': '#089E00', 'Owned by Other': '#FF1100'}
    else:
        efficiency_df = efficiency_df.with_columns(pl.lit('N/A').alias('Status'))
        color_map = {'N/A': '#1100FF'}

    # Convert to pandas for Plotly integration
    plot_df = efficiency_df.to_pandas()

    # Create the scatter plot
    fig = px.scatter(
        plot_df,
        x='Actual Points',
        y='Expected Points',
        color='Status',
        color_discrete_map=color_map,
        custom_data=['Player', 'Efficiency', 'Owner'],
        title="Player Efficiency: Actual vs. Expected Fantasy Point Production"
    )

    # Add the y=x line
    max_val = max(efficiency_df['Actual Points'].max(), efficiency_df['Expected Points'].max())
    max_val = max_val * 1.05 # Small buffer
    fig.add_shape(
        type="line",
        x0=0, y0=0, x1=max_val, y1=max_val,
        line=dict(color="grey", width=1, dash="dash"),
        name="Expected Efficiency"
    )

    fig.update_layout(
        xaxis_title="Expected Fantasy Points",
        yaxis_title="Actual Fantasy Points",
        hovermode="closest",
        font_color='black',
        legend_title_text='Ownership',
        # Ensure the line is visible even if data is sparse
        xaxis_range=[0, max_val],
        yaxis_range=[0, max_val]
    )

    # Customize the hover text.
    fig.update_traces(
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>" +
            "Owner: %{customdata[2]}<br>" +
            "Actual Points: %{y:.2f}<br>" +
            "Expected Points: %{x:.2f}<br>" +
            "Efficiency: %{customdata[1]:+.2f}" +
            "<extra></extra>"  # Hides the secondary box
        )
    )

    return fig


if __name__ == '__main__':
    pl.Config(tbl_rows=-1, tbl_cols=-1)

    from efficiency import compute_efficiency
    league_id = input('Enter Sleeper platform league number (This is found in the sleeper url):')
    efficiency_df = compute_efficiency(league_id, offseason=True).filter(pl.col('pos') == 'RB')
    create_efficiency_chart(efficiency_df, user_name=None).show()