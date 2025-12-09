"""
This module contains functions for creating visualizations for the dashboard.
"""

import polars as pl
import plotly.graph_objects as go
import plotly.express as px

from nflreadpy import get_current_week


def create_tier_chart(board_df: pl.DataFrame, user_name: str | None) -> go.Figure:
    """
    Creates an interactive tier chart showing player ECR with best/worst error bars.

    Args:
        board_df (pl.DataFrame): A DataFrame containing player data with tiers. Should originate from src.tiers.create_tiers().
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
        title="Positional Ranking Tiers",
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
        efficiency_df (pl.DataFrame): A DataFrame containing player efficiency data. Should originate from src.efficiency.compute_efficiency().
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
        color_map = {user_name: '#1100FF', 'Free Agent': '#089E00', 'Owned by Other': '#6c757d'}
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
        title="Actual vs. Expected Fantasy Point Production"
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
        height=750,
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


def create_rec_share_chart(share_df: pl.DataFrame, user_name: str | None = None) -> go.Figure:
    """
        Creates an interactive scatter plot showing target and production share statistics.

        Args:
            share_df (pl.DataFrame): A DataFrame containing player receiving share data. Should originate from src.advanced_stats.receiving_share().
            user_name (str, optional): The name of the user to highlight. Players owned by this user will be labeled. Defaults to None.

        Returns:
            go.Figure: A Plotly figure object ready to be displayed in a dcc.Graph.
        """
    if share_df.is_empty():
        # Return an empty figure if there's no data
        return go.Figure()

    # Filter out low share players.
    share_df = share_df.filter((pl.col('WOPR') >= 0.1))

    # Add an ownership status column for dynamic coloring
    if user_name and 'Owner' in share_df.columns:
        share_df = share_df.with_columns(
            pl.when(pl.col('Owner') == user_name).then(
                pl.lit(user_name)
            ).when(
                pl.col('Owner') == 'Free Agent'
            ).then(pl.lit('Free Agent')
                   ).otherwise(
                pl.lit('Owned by Other')
            ).alias('Status')
        )
        color_map = {user_name: '#1100FF', 'Free Agent': '#089E00', 'Owned by Other': '#6c757d'}
    else:
        share_df = share_df.with_columns(pl.lit('N/A').alias('Status'))
        color_map = {'N/A': '#1100FF'}

    # Convert to pandas for Plotly integration
    plot_df = share_df.to_pandas()

    # Create the scatter plot
    fig = px.scatter(
        plot_df,
        x='WOPR',
        y='Receiving Yard Share',
        color='Status',
        color_discrete_map=color_map,
        custom_data=['Player', 'Owner'],
        title="Quality of Receiving Targets Vs. Share of Receiving Yards"
    )

    # --- Calculate and Add Linear Regression ---
    x_col, y_col = 'WOPR', 'Receiving Yard Share'
    x_mean = share_df[x_col].mean()
    y_mean = share_df[y_col].mean()
    xy_cov = pl.cov(share_df[x_col], share_df[y_col], eager=True).item()
    x_var = share_df[x_col].var()

    slope = xy_cov / x_var
    intercept = y_mean - slope * x_mean

    x0 = share_df.select(x_col).min().item()
    x1 = share_df.select(x_col).max().item()
    y0 = slope * x0 + intercept
    y1 = slope * x1 + intercept

    # Regression Line
    fig.add_shape(
        type="line",
        x0=x0, y0=y0, x1=x1, y1=y1,
        line=dict(color="grey", width=1, dash="dash"),
        name="Expected Share"
    )

    fig.update_layout(
        height=750,
        yaxis_title="Receiving Yard Share",
        xaxis_title="Weighted Opportunity Rating (WOPR)",
        hovermode="closest",
        font_color='black',
        legend_title_text='Ownership',
        # Set axis ranges to give a bit of padding
        xaxis_range=[share_df[x_col].min() * 0.9, share_df[x_col].max() * 1.1],
        yaxis_range=[share_df[y_col].min() * 0.9, share_df[y_col].max() * 1.1]
    )

    # Customize the hover text.
    fig.update_traces(
        hovertemplate=(
                "<b>%{customdata[0]}</b><br>" +
                "Owner: %{customdata[1]}<br>" +
                "WOPR: %{x:.2f}<br>" +
                "Rec Yard Share: %{y:.2f}<br>" +
                "<extra></extra>"  # Hides the secondary box
        )
    )

    return fig

def create_rush_share_chart(share_df: pl.DataFrame, user_name: str | None = None) -> go.Figure:
    """
        Creates an interactive scatter plot showing rushing share and rushing production share statistics.

        Args:
            share_df (pl.DataFrame): A DataFrame containing player rushing share data. Should originate from src.advanced_stats.rushing_share().
            user_name (str, optional): The name of the user to highlight. Players owned by this user will be labeled. Defaults to None.

        Returns:
            go.Figure: A Plotly figure object ready to be displayed in a dcc.Graph.
        """
    if share_df.is_empty():
        # Return an empty figure if there's no data
        return go.Figure()

    # Filter out low share players.
    share_df = share_df.filter((pl.col('Rushing Attempt Share') >= 0.1))

    # Add an ownership status column for dynamic coloring
    if user_name and 'Owner' in share_df.columns:
        share_df = share_df.with_columns(
            pl.when(pl.col('Owner') == user_name).then(
                pl.lit(user_name)
            ).when(
                pl.col('Owner') == 'Free Agent'
            ).then(pl.lit('Free Agent')
                   ).otherwise(
                pl.lit('Owned by Other')
            ).alias('Status')
        )
        color_map = {user_name: '#1100FF', 'Free Agent': '#089E00', 'Owned by Other': '#6c757d'}
    else:
        share_df = share_df.with_columns(pl.lit('N/A').alias('Status'))
        color_map = {'N/A': '#1100FF'}

    # Convert to pandas for Plotly integration
    plot_df = share_df.to_pandas()

    # Create the scatter plot
    fig = px.scatter(
        plot_df,
        x='Rushing Attempt Share',
        y='Rushing Yard Share',
        color='Status',
        color_discrete_map=color_map,
        custom_data=['Player', 'Owner'],
        title="Share of Rushing Attempts Vs. Share of Rushing Yards"
    )

    # --- Calculate and Add Linear Regression ---
    x_col, y_col = 'Rushing Attempt Share', 'Rushing Yard Share'
    x_mean = share_df[x_col].mean()
    y_mean = share_df[y_col].mean()
    xy_cov = pl.cov(share_df[x_col], share_df[y_col], eager=True).item()
    x_var = share_df[x_col].var()

    slope = xy_cov / x_var
    intercept = y_mean - slope * x_mean

    x0 = share_df.select(x_col).min().item()
    x1 = share_df.select(x_col).max().item()
    y0 = slope * x0 + intercept
    y1 = slope * x1 + intercept

    # Regression Line
    fig.add_shape(
        type="line",
        x0=x0, y0=y0, x1=x1, y1=y1,
        line=dict(color="grey", width=1, dash="dash"),
        name="Expected Share"
    )

    fig.update_layout(
        height=750,
        yaxis_title="Rushing Yard Share",
        xaxis_title="Rushing Attempt Share",
        hovermode="closest",
        font_color='black',
        legend_title_text='Ownership',
        # Set axis ranges to give a bit of padding
        xaxis_range=[share_df[x_col].min() * 0.9, share_df[x_col].max() * 1.1],
        yaxis_range=[share_df[y_col].min() * 0.9, share_df[y_col].max() * 1.1]
    )

    # Customize the hover text.
    fig.update_traces(
        hovertemplate=(
                "<b>%{customdata[0]}</b><br>" +
                "Owner: %{customdata[1]}<br>" +
                "Attempt Share: %{x:.2f}<br>" +
                "Rush Yard Share: %{y:.2f}<br>" +
                "<extra></extra>"  # Hides the secondary box
        )
    )

    return fig