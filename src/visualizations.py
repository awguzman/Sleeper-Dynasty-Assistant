"""
This module contains functions for creating visualizations for the dashboard.
"""

import polars as pl
import plotly.graph_objects as go
import plotly.express as px

from nflreadpy import get_current_week

from src.advanced_stats import receiver_separation


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


def create_share_chart(share_df: pl.DataFrame, user_name: str | None = None) -> go.Figure:
    """
        Creates an interactive scatter plot showing receiver target and air yard share statistics.

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
    share_df = share_df.filter((pl.col('Air Yards Share') >= 0.05) | (pl.col('Target Share') >= 0.05))

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
        y='Air Yards Share',
        x='Target Share',
        color='Status',
        color_discrete_map=color_map,
        custom_data=['Player', 'WOPR', 'Owner'],
        title="Volume of Targets Versus Quality of Targets"
    )

    # --- Calculate and Add Linear Regression ---
    x_col, y_col = 'Target Share', 'Air Yards Share'
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
        yaxis_title="Air Yard Share",
        xaxis_title="Target Share",
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
                "Owner: %{customdata[2]}<br>" +
                "Target Share: %{x:.2f}<br>" +
                "Air Yard Share: %{y:.2f}<br>" +
                "WOPR: %{customdata[1]:.2f}" +
                "<extra></extra>"  # Hides the secondary box
        )
    )

    return fig


def create_box_chart(box_df: pl.DataFrame, user_name: str | None = None) -> go.Figure:
    """
        Creates an interactive scatter plot showing stacked box rushing efficiency.

        Args:
            box_df (pl.DataFrame): A DataFrame containing player rushing data. Should originate from src.advanced_stats.stacked_box_efficiency().
            user_name (str, optional): The name of the user to highlight. Players owned by this user will be labeled. Defaults to None.

        Returns:
            go.Figure: A Plotly figure object ready to be displayed in a dcc.Graph.
        """
    if box_df.is_empty():
        return go.Figure

    # Limit to players who average 5 touches per game.
    box_df = box_df.filter(pl.col('Rush Attempts') > 5 * get_current_week())

    # Add an ownership status column for dynamic coloring
    if user_name and 'Owner' in box_df.columns:
        box_df = box_df.with_columns(
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
        box_df = box_df.with_columns(pl.lit('N/A').alias('Status'))
        color_map = {'N/A': '#1100FF'}

    # Convert to pandas for Plotly integration
    plot_df = box_df.to_pandas()

    # Create the scatter plot
    fig = px.scatter(
        plot_df,
        x='Stacked Box Percentage',
        y='Rush Yards over Expected per Attempt',
        size='Rush Attempts',  # Bubble size based on rush attempts
        color='Status',
        color_discrete_map=color_map,
        custom_data=['Player', 'Owner', 'Rush Attempts'],
        title="Rushing Efficiency Versus Situational Difficulty"
    )

    # Add quadrant lines
    fig.add_vline(x=box_df['Stacked Box Percentage'].mean(), line_width=1, line_dash="dash", line_color="grey")
    fig.add_hline(y=0, line_width=1, line_dash="dash", line_color="grey")

    # Set axis ranges
    x_range = [box_df['Stacked Box Percentage'].min() * 0.9,
               box_df['Stacked Box Percentage'].max() * 1.1]
    y_range = [box_df['Rush Yards over Expected per Attempt'].min() * 0.9,
               box_df['Rush Yards over Expected per Attempt'].max() * 1.1]

    # Add quadrant labels
    fig.add_annotation(
        x=x_range[0], y=y_range[1], text="<b>Good Situation, Good Efficiency</b>",
        showarrow=False, xanchor='left', yanchor='top', font=dict(color="#555", size=14)
    )
    fig.add_annotation(
        x=x_range[1], y=y_range[1], text="<b>Bad Situation, Good Efficiency</b>",
        showarrow=False, xanchor='right', yanchor='top', font=dict(color="#555", size=14)
    )
    fig.add_annotation(
        x=x_range[0], y=y_range[0], text="<b>Good Situation, Bad Efficiency</b>",
        showarrow=False, xanchor='left', yanchor='bottom', font=dict(color="#555", size=14)
    )
    fig.add_annotation(
        x=x_range[1], y=y_range[0], text="<b>Bad Situation, Bad Efficiency</b>",
        showarrow=False, xanchor='right', yanchor='bottom', font=dict(color="#555", size=14)
    )

    fig.update_layout(
        height=750,
        xaxis_title="Stacked Box Percentage",
        yaxis_title="Rush Yards over Expected per Attempt",
        hovermode="closest",
        font_color='black',
        legend_title_text='Ownership',
        # Set axis ranges to give a bit of padding
        xaxis_range=x_range,
        yaxis_range=y_range
    )

    # Customize the hover text.
    fig.update_traces(
        hovertemplate=(
                "<b>%{customdata[0]}</b><br>" +
                "Owner: %{customdata[1]}<br>" +
                "Stacked Box %: %{x:.2f}<br>" +
                "RYOE/Att: %{y:.2f}<br>" +
                "Rush Attempts: %{customdata[2]}" +
                "<extra></extra>"  # Hides the secondary box
        )
    )

    return fig


def create_separation_chart(separation_df: pl.DataFrame, user_name: str | None = None) -> go.Figure:
    """
    Creates an interactive scatter plot showing receiver separation vs. cushion.

    Args:
        separation_df (pl.DataFrame): A DataFrame with separation and cushion data.
        user_name (str, optional): The name of the user to highlight.

    Returns:
        go.Figure: A Plotly figure object.
    """
    if separation_df.is_empty():
        return go.Figure()

    # Limit to players who average at least 3 target per game.
    separation_df = separation_df.filter(pl.col('targets') >= 3 * get_current_week())


    # Add an ownership status column for dynamic coloring
    if user_name and 'Owner' in separation_df.columns:
        separation_df = separation_df.with_columns(
            pl.when(pl.col('Owner') == user_name).then(pl.lit(user_name))
            .when(pl.col('Owner') == 'Free Agent').then(pl.lit('Free Agent'))
            .otherwise(pl.lit('Owned by Other')).alias('Status')
        )
        color_map = {user_name: '#1100FF', 'Free Agent': '#28a745', 'Owned by Other': '#6c757d'}
    else:
        separation_df = separation_df.with_columns(pl.lit('N/A').alias('Status'))
        color_map = {'N/A': '#1100FF'}

    # Convert to pandas for Plotly integration
    plot_df = separation_df.to_pandas()

    # Create the scatter plot
    fig = px.scatter(
        plot_df,
        x='Cushion',
        y='Separation',
        size='targets',  # Bubble size based on targets
        color='Status',
        color_discrete_map=color_map,
        custom_data=['Player', 'Owner', 'targets'],
        title="Receiving Separation Versus Cushion Given"
    )

    # --- Add Quadrant Lines and Annotations ---
    mean_cushion = separation_df['Cushion'].mean()
    mean_separation = separation_df['Separation'].mean()

    fig.add_vline(x=mean_cushion, line_width=1, line_dash="dash", line_color="grey")
    fig.add_hline(y=mean_separation, line_width=1, line_dash="dash", line_color="grey")

    x_range = [separation_df['Cushion'].min() * 0.9, separation_df['Cushion'].max() * 1.1]
    y_range = [separation_df['Separation'].min() * 0.9, separation_df['Separation'].max() * 1.1]

    # fig.add_annotation(
    #     x=x_range[1], y=y_range[1], text="<b>Elite Route Runners</b>",
    #     showarrow=False, xanchor='right', yanchor='top', font=dict(color="#555", size=14)
    # )
    fig.add_annotation(
        x=x_range[0], y=y_range[1], text="<b>Good Route Running</b>",
        showarrow=False, xanchor='left', yanchor='top', font=dict(color="#555", size=14)
    )
    fig.add_annotation(
        x=x_range[1], y=y_range[0], text="<b>Bad Route Running</b>",
        showarrow=False, xanchor='right', yanchor='bottom', font=dict(color="#555", size=14)
    )
    # fig.add_annotation(
    #     x=x_range[0], y=y_range[0], text="<b>Struggling to Separate</b>",
    #     showarrow=False, xanchor='left', yanchor='bottom', font=dict(color="#555", size=14)
    # )

    fig.update_layout(
        height=750,
        xaxis_title="Average Cushion at Snap (Yards)",
        yaxis_title="Average Separation at Target (Yards)",
        hovermode="closest",
        font_color='black',
        legend_title_text='Ownership',
        xaxis_range=x_range,
        yaxis_range=y_range
    )

    fig.update_traces(
        hovertemplate=(
            "<b>%{customdata[0]}</b></br>" +
            "Owner: %{customdata[1]}<br>" +
            "Avg. Cushion: %{x:.2f} yds<br>" +
            "Avg. Separation: %{y:.2f} yds<br>" +
            "Targets: %{customdata[2]}" +
            "<extra></extra>"
        )
    )

    return fig


def create_qb_playstyle_chart(qb_df: pl.DataFrame, user_name: str | None = None) -> go.Figure:
    """
    Creates an interactive bubble chart showing QB playstyle (aggressiveness vs. efficiency).

    Args:
        qb_df (pl.DataFrame): A DataFrame with QB playstyle data. Typically arrives from src.advanced_stats.qb_playstyle().
        user_name (str, optional): The name of the user to highlight.

    Returns:
        go.Figure: A Plotly figure object.
    """
    if qb_df.is_empty():
        return go.Figure()

    # Limit to players who average at least 15 pass attempts per game.
    qb_df = qb_df.filter(pl.col('attempts') >= 15 * get_current_week())

    # Add an ownership status column for dynamic coloring
    if user_name and 'Owner' in qb_df.columns:
        qb_df = qb_df.with_columns(
            pl.when(pl.col('Owner') == user_name).then(pl.lit(user_name))
            .when(pl.col('Owner') == 'Free Agent').then(pl.lit('Free Agent'))
            .otherwise(pl.lit('Owned by Other')).alias('Status')
        )
        color_map = {user_name: '#1100FF', 'Free Agent': '#089E00', 'Owned by Other': '#6c757d'}
    else:
        qb_df = qb_df.with_columns(pl.lit('N/A').alias('Status'))
        color_map = {'N/A': '#1100FF'}

    # Convert to pandas for Plotly integration
    plot_df = qb_df.to_pandas()

    # Create the bubble scatter plot
    fig = px.scatter(
        plot_df,
        x='Aggressiveness',
        y='CPOE',
        size='attempts',  # Bubble size based on pass attempts
        color='Status',
        color_discrete_map=color_map,
        custom_data=['Player', 'Owner', 'attempts'],
        title="Passing Aggressiveness Versus Completion Efficiency"
    )

    # --- Add Quadrant Lines and Annotations ---
    mean_x = qb_df['Aggressiveness'].mean()
    mean_y = qb_df['CPOE'].mean()

    fig.add_vline(x=mean_x, line_width=1, line_dash="dash", line_color="grey")
    fig.add_hline(y=mean_y, line_width=1, line_dash="dash", line_color="grey")

    x_range = [qb_df['Aggressiveness'].min() * 0.95, qb_df['Aggressiveness'].max() * 1.05]
    y_range = [qb_df['CPOE'].min() * 1.1, qb_df['CPOE'].max() * 1.1]

    fig.add_annotation(
        x=x_range[0], y=y_range[1], text="<b>Accurate & Conservative</b>",
        showarrow=False, xanchor='left', yanchor='top', font=dict(color="#555", size=14)
    )
    fig.add_annotation(
        x=x_range[1], y=y_range[1], text="<b>Accurate & Aggressive</b>",
        showarrow=False, xanchor='right', yanchor='top', font=dict(color="#555", size=14)
    )
    # fig.add_annotation(
    #     x=x_range[0], y=y_range[0], text="<b>Struggling</b>",
    #     showarrow=False, xanchor='left', yanchor='bottom', font=dict(color="#555", size=14)
    # )
    fig.add_annotation(
        x=x_range[1], y=y_range[0], text="<b>Inaccurate & Aggressive</b>",
        showarrow=False, xanchor='right', yanchor='bottom', font=dict(color="#555", size=14)
    )

    fig.update_layout(
        height=750,
        xaxis_title="Aggressiveness (% of throws into tight windows)",
        yaxis_title="Completion % Above Expectation (CPOE)",
        hovermode="closest",
        font_color='black',
        legend_title_text='Ownership'
    )

    fig.update_traces(
        hovertemplate=(
            "<b>%{customdata[0]}</b><br>" +
            "Owner: %{customdata[1]}<br><br>" +
            "Aggressiveness: %{x:.2f}%<br>" +
            "CPOE: %{y:+.2f}<br>" +
            "Pass Attempts: %{customdata[2]}" +
            "<extra></extra>"
        )
    )

    return fig