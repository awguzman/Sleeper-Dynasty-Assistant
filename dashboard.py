"""
This module defines the layout and callback logic for the Sleeper Dynasty Assistant dashboard.
"""

# --- Backend Imports ---
import polars as pl
import io

# --- Dashboard Imports ---
import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go

# --- Import Helper Functions ---
from src.boards import create_board
from src.league import get_league_info
from src.tiers import create_tiers
from src.trade import create_trade_values
# from src.efficiency import compute_efficiency
from src.advanced_stats import compute_efficiency, receiving_share, stacked_box_efficiency, receiver_separation, qb_aggressiveness
from src.visualizations import (create_tier_chart, create_efficiency_chart,  create_share_chart, create_box_chart,
                                create_separation_chart, create_qb_playstyle_chart)

# --- Configure nflreadpy Cache ---
from pathlib import Path
from nflreadpy.config import update_config

cache_dir = Path(__file__).resolve().parent / 'cache'
update_config(cache_mode="filesystem", cache_dir=cache_dir, verbose=True, cache_duration=3600)

# Initialize the Dash application. Suppress callback exceptions due to dynamic layout.
app = dash.Dash(__name__, suppress_callback_exceptions=True)

# Server variable
server = app.server

# --- App Layout ---
# The layout is the root component that describes the application's appearance.
app.layout = html.Div([
    # --- Data Stores ---
    # These hidden components store the results of expensive computations.
    dcc.Store(id='draft-positional-board-store'),
    dcc.Store(id='draft-overall-board-store'),
    dcc.Store(id='weekly-board-store'),
    dcc.Store(id='league-info-store'),

    # --- Header Section ---
    html.Div([
        html.H1("Sleeper Dynasty Assistant"),
        html.A(
            "Github",
            href="https://github.com/awguzman/Sleeper-Dynasty-Assistant",
            target="_blank",  # This opens the link in a new tab
            style={'fontSize': '12px', 'textDecoration': 'none'}
        )
    ], style={'display': 'flex', 'justifyContent': 'space-between', 'alignItems': 'center', 'padding': '0px 25px'}),

    # --- Global Controls ---
    # These inputs for league and owner are placed outside the tabs to be persistent
    html.Div(children=[
        # League ID Input
        html.Div([
            html.Label("Enter Sleeper League ID: ", style={'margin-right': '10px'}),
            dcc.Input(
                id='league-id-input',
                type='text',
                placeholder='e.g., 992016434344030208'
            ),
        ], style={'display': 'flex', 'align-items': 'center', 'margin-right': '50px', 'padding': '0px 25px'}),

        # Owner Name Dropdown
        html.Div([
            html.Label("Select Owner: ", style={'margin-right': '10px'}),
            dcc.Dropdown(
                id='owner-name-dropdown',
                placeholder='Your username',
                disabled=True, # Disabled until league_id provided.
                style={'width': '250px'}
            ),
        ], style={'display': 'flex', 'align-items': 'center'}),
    ], style={'display': 'flex', 'align-items': 'center'}),
    html.Br(),


    # --- Main Tabbed Interface ---
    dcc.Tabs(className='top-tabs-container', children=[
        # --- Top Level Tab: Draft Tools ---
        dcc.Tab(label='Draft Tools', className='custom-top-tab', selected_className='custom-top-tab-selected', children=[
            # --- Nested Tabs for parent Draft Tools tab
            dcc.Tabs(className='nested-tabs-container', children=[
                # --- Draft Board tab ---
                dcc.Tab(label='Draft Board', className='custom-nested-tab', selected_className='custom-nested-tab-selected', children=[
                    html.Br(),
                    html.Div([
                        # Group for left-aligned items
                        html.Div([
                            html.Label("Position: ", style={'margin-right': '20px'}),
                            # Position choices.
                            dcc.RadioItems(
                                id='position-draft-selection',
                                options=[
                                    {'label': 'Overall', 'value': 'Overall'},
                                    {'label': 'Quarterback', 'value': 'QB'},
                                    {'label': 'Running Back', 'value': 'RB'},
                                    {'label': 'Wide Receiver', 'value': 'WR'},
                                    {'label': 'Tight End', 'value': 'TE'},
                                ],
                                value='Overall',  # Default value
                                inline=True,  # Display options horizontally
                                labelStyle={'margin-right': '20px'}  # Add space between radio items
                            ),
                        ], style={'display': 'flex', 'align-items': 'center', 'padding': '0px 25px'}),

                        # Show taken players checkbox
                        dcc.Checklist(
                            id='show-taken-draft-checkbox',
                            options=[{'label': 'Show Taken Players', 'value': 'show_taken'}],
                            value=[],  # Default to unchecked
                        ),
                    ], style={'display': 'flex', 'align-items': 'center', 'justify-content': 'space-between', 'padding': '0px 25px'}),
                    html.Br(),

                    # Draft board table
                    html.Div(style={'padding': '0px 25px'}, children=[
                        dcc.Loading(
                            id='loading-draft-table',
                            type='circle',
                            children=[
                                # Add a placeholder for the "Last Update" text
                                html.Div(id='draft-last-update', style={'text-align': 'right', 'color': 'grey',
                                                                        'font-style': 'italic',
                                                                        'margin-bottom': '5px'}),
                                dash_table.DataTable(
                                    id='draft-table',
                                    style_data_conditional=[],
                                    style_table={'overflowX': 'auto'},
                                    style_header={
                                        'fontWeight': 'bold'
                                    },
                                    # Base styles for all cells
                                    style_cell={
                                        'textAlign': 'left',
                                        'padding': '5px',
                                        'whiteSpace': 'normal',
                                        'height': 'auto',
                                    },
                                    # Conditional styles for specific columns
                                    style_cell_conditional=[
                                        {
                                            'if': {'column_id': ['Player', 'Owner']},
                                            'width': '180px', 'minWidth': '180px', 'maxWidth': '250px',
                                        },
                                        {
                                            'if': {'column_id': ['Team', 'ECR', 'Best', 'Worst', 'Std', 'Age', 'Bye']},
                                            'width': '80px', 'minWidth': '80px', 'maxWidth': '80px',
                                        }
                                    ]
                                )
                            ]
                        )
                    ]
                             ),
                    # Bottom text box
                    html.Hr(),
                    dcc.Markdown("""
                    Note: This table does not take into consideration in-season performance. It should be considered 
                    outdated following the first week of play.
                
                    *   **ECR**: Expert Consensus Ranking. The (weighted) average rank given to a player from all experts surveyed by FantasyPros.
                    *   **Best/Worst**: Most optimistic (lowest)/pessimistic (highest) ranking given to a player by any one expert.
                    *   **Std**: Standard deviation of rankings given to a player from all experts. Smaller values mean higher agreement. 
                
                    """, style={'color': 'grey', 'font-style': 'italic', 'padding-left': '20px', 'padding-top': '10px'})
                ]),
                # --- Draft Tiers tab ---
                dcc.Tab(label='Draft Tiers', className='custom-nested-tab', selected_className='custom-nested-tab-selected', children=[
                    html.Br(),
                    html.Div([
                        # Position selection
                        html.Div([
                            html.Label("Position: ", style={'margin-right': '20px'}),
                            dcc.RadioItems(
                                id='position-draft-tier-selection',
                                options=[
                                    {'label': 'Quarterback', 'value': 'QB'},
                                    {'label': 'Running Back', 'value': 'RB'},
                                    {'label': 'Wide Receiver', 'value': 'WR'},
                                    {'label': 'Tight End', 'value': 'TE'},
                                ],
                                value='QB',  # Default value
                                inline=True,
                                labelStyle={'margin-right': '20px'}
                            ),
                        ], style={'display': 'flex', 'align-items': 'center', 'padding': '0px 25px'}),
                    ], style={'display': 'flex', 'align-items': 'center', 'justify-content': 'space-between'}),
                    html.Br(),

                    dcc.Loading(
                        id='loading-draft-tier-chart',
                        type='circle',
                        # Graph component to display the Plotly figure
                        children=dcc.Graph(id='draft-tier-chart-graph')
                    ),

                    # Bottom text box
                    html.Hr(),
                    dcc.Markdown("""
                    Uses a Gaussian Mixture Model (GMM) together with Bayesian Information Criterion (BIC) to dynamically 
                    cluster players into statistically similar tiers. This should be viewed as a measure of how similar any two 
                    players are ranked by FantasyPros.
                
                    Inspired by analysis of Boris Chen, see www.borischen.co
                    
                    Note: This does not take into consideration in-season performance. It should be considered 
                    outdated following the first week of play.
                    """, style={'color': 'grey', 'font-style': 'italic', 'padding-left': '20px', 'padding-top': '10px'})

                ]),
                # --- Offseason Trade Values tab ---
                dcc.Tab(label='Dynasty Trade Values', className='custom-nested-tab', selected_className='custom-nested-tab-selected', children=[
                    html.Br(),
                    # Container for side-by-side tables
                    html.Div(children=[
                        # QB Table
                        html.Div(children=[
                            html.H4("Quarterback", style={'textAlign': 'center'}),
                            dcc.Loading(type='circle', children=dash_table.DataTable(
                                id='trade-value-table-qb',
                                style_table={'height': '600px', 'overflowY': 'auto'}, # Fix table height and add scroll bar.
                                style_header={'fontWeight': 'bold'},
                                style_cell={'textAlign': 'left', 'padding': '5px'},
                                style_cell_conditional=[
                                    {'if': {'column_id': 'Player'}, 'width': '50%'},
                                    {'if': {'column_id': ['Age', 'Value']}, 'width': '25%'}
                                ]
                            )),
                        ], style={'flex': 1, 'padding': '0px 10px'}),
                        # RB Table
                        html.Div([
                            html.H4("Running Back", style={'textAlign': 'center'}),
                            dcc.Loading(type='circle', children=dash_table.DataTable(
                                id='trade-value-table-rb',
                                style_table={'height': '600px', 'overflowY': 'auto'},
                                # Fix table height and add scroll bar.
                                style_header={'fontWeight': 'bold'},
                                style_cell={'textAlign': 'left', 'padding': '5px'},
                                style_cell_conditional=[
                                    {'if': {'column_id': 'Player'}, 'width': '50%'},
                                    {'if': {'column_id': ['Age', 'Value']}, 'width': '25%'}
                                ]
                            )),
                        ], style={'flex': 1, 'padding': '0px 10px'}),
                        # WR Table
                        html.Div([
                            html.H4("Wide Receiver", style={'textAlign': 'center'}),
                            dcc.Loading(type='circle', children=dash_table.DataTable(
                                id='trade-value-table-wr',
                                style_table={'height': '600px', 'overflowY': 'auto'},
                                # Fix table height and add scroll bar.
                                style_header={'fontWeight': 'bold'},
                                style_cell={'textAlign': 'left', 'padding': '5px'},
                                style_cell_conditional=[
                                    {'if': {'column_id': 'Player'}, 'width': '50%'},
                                    {'if': {'column_id': ['Age', 'Value']}, 'width': '25%'}
                                ]
                            )),
                        ], style={'flex': 1, 'padding': '0px 10px'}),
                        # TE Table
                        html.Div([
                            html.H4("Tight End", style={'textAlign': 'center'}),
                            dcc.Loading(type='circle', children=dash_table.DataTable(
                                id='trade-value-table-te',
                                style_table={'height': '600px', 'overflowY': 'auto'},
                                # Fix table height and add scroll bar.
                                style_header={'fontWeight': 'bold'},
                                style_cell={'textAlign': 'left', 'padding': '5px'},
                                style_cell_conditional=[
                                    {'if': {'column_id': 'Player'}, 'width': '50%'},
                                    {'if': {'column_id': ['Age', 'Value']}, 'width': '25%'}
                                ]
                            )),
                        ], style={'flex': 1, 'padding': '0px 10px'}),
                    ], style={'display': 'flex', 'flexDirection': 'row', 'padding': '0px 25px'}),
                html.Hr(),
                dcc.Markdown("""
                    Trade values are based on overall dynasty ECR values. They will (possibly over)emphasize long term value
                    over short-term gain.
                    
                    Note: This does not take into consideration in-season performance. It should be considered 
                    outdated following the first week of play.
                    """, style={'color': 'grey', 'font-style': 'italic', 'padding-left': '25px', 'padding-top': '10px'})
                ]),
            ]),
        ]),
        # --- Top Level Tab: In-Season Tools ---
        dcc.Tab(label='In-Season Tools', className='custom-top-tab', selected_className='custom-top-tab-selected', children=[
            # --- Nested Tabs for parent In-Season Tools tab
            dcc.Tabs(className='nested-tabs-container', children=[
                # --- Draft Board tab ---
                dcc.Tab(label='Weekly Projections', className='custom-nested-tab', selected_className='custom-nested-tab-selected', children=[
                    html.Br(),
                    html.Div([
                        # Position selection
                        html.Div([
                            html.Label("Position: ", style={'margin-right': '20px'}),
                            dcc.RadioItems(
                                id='position-proj-selection',
                                options=[
                                    {'label': 'Quarterback', 'value': 'QB'},
                                    {'label': 'Running Back', 'value': 'RB'},
                                    {'label': 'Wide Receiver', 'value': 'WR'},
                                    {'label': 'Tight End', 'value': 'TE'},
                                ],
                                value='QB',  # Default value
                                inline=True,  # Display options horizontally
                                labelStyle={'margin-right': '20px'}  # Add space between radio items
                            ),
                        ], style={'display': 'flex', 'align-items': 'center', 'padding': '0px 25px'}),

                        # Show taken players checkbox
                        dcc.Checklist(
                            id='show-taken-proj-checkbox',
                            options=[{'label': 'Show Taken Players', 'value': 'show_taken'}],
                            value=[],  # Default to unchecked
                        ),
                    ], style={'display': 'flex', 'align-items': 'center', 'justify-content': 'space-between', 'padding': '0px 25px'}),

                    html.Br(),

                    # Weekly projections table
                    html.Div(style={'padding': '0px 25px'}, children=[
                        dcc.Loading(
                            id='loading-proj-table',
                            type='circle',
                            children=[
                                # Add a placeholder for the "Last Update" text
                                html.Div(id='proj-last-update', style={'text-align': 'right', 'color': 'grey',
                                                                       'font-style': 'italic', 'margin-bottom': '5px'}),
                                dash_table.DataTable(
                                    id='proj-table',
                                    style_data_conditional=[],
                                    style_table={'overflowX': 'auto'},
                                    style_header={
                                        'fontWeight': 'bold'
                                    },
                                    # Base styles for all cells
                                    style_cell={
                                        'textAlign': 'left',
                                        'padding': '5px',
                                        'whiteSpace': 'normal',
                                        'height': 'auto',
                                    },
                                    # Conditional styles for specific columns
                                    style_cell_conditional=[
                                        {
                                            'if': {'column_id': ['Player', 'Owner']},
                                            'width': '150px', 'minWidth': '150px', 'maxWidth': '250px',
                                        },
                                        {
                                            'if': {
                                                'column_id': ['ECR', 'Team', 'Opponent', 'Start Grade', 'Best', 'Worst',
                                                              'Std', 'Rank', 'Proj. Points']},
                                            'width': '80px', 'minWidth': '80px', 'maxWidth': '80px',
                                        }
                                    ]
                                )
                            ]
                        )
                    ]),

                    # Bottom text box
                    html.Hr(),
                    dcc.Markdown("""
                    Note: "Last Update" refers to the last update of data provided by FantasyPros. This application has no 
                    control over the frequency of such updates.
                
                    *   **ECR**: Expert Consensus Ranking. The (weighted) average rank given to a player from all experts surveyed by FantasyPros.
                    *   **Best**: Most optimistic (lowest) ranking given to a player by any one expert.
                    *   **Worst**: Most pessimistic (highest) ranking given to a player by any one expert.
                    *   **Std**: Standard deviation of rankings given to a player from all experts. Smaller values mean higher agreement. 
                
                    """, style={'color': 'grey', 'font-style': 'italic', 'padding-left': '20px', 'padding-top': '10px'})
                ]),
                # --- Draft Tiers tab ---
                dcc.Tab(label='Weekly Tiers', className='custom-nested-tab', selected_className='custom-nested-tab-selected', children=[
                    html.Br(),
                    html.Div([
                        # Position selection
                        html.Div([
                            html.Label("Position: ", style={'margin-right': '20px'}),
                            dcc.RadioItems(
                                id='position-weekly-tier-selection',
                                options=[
                                    {'label': 'Quarterback', 'value': 'QB'},
                                    {'label': 'Running Back', 'value': 'RB'},
                                    {'label': 'Wide Receiver', 'value': 'WR'},
                                    {'label': 'Tight End', 'value': 'TE'},
                                ],
                                value='QB',  # Default value
                                inline=True,
                                labelStyle={'margin-right': '20px'}
                            ),
                        ], style={'display': 'flex', 'align-items': 'center', 'padding': '0px 25px'}),
                    ], style={'display': 'flex', 'align-items': 'center', 'justify-content': 'space-between'}),
                    html.Br(),

                    dcc.Loading(
                        id='loading-weekly-tier-chart',
                        type='circle',
                        # Graph component to display the Plotly figure
                        children=dcc.Graph(id='weekly-tier-chart-graph')
                    ),

                    # Bottom text box
                    html.Hr(),
                    dcc.Markdown("""
                    Uses a Gaussian Mixture Model (GMM) together with Bayesian Information Criterion (BIC) to dynamically 
                    cluster players into statistically similar tiers. This should be viewed as a measure of how similar any two 
                    players are ranked by FantasyPros.
                
                    Inspired by analysis of Boris Chen, see www.borischen.co
                    """, style={'color': 'grey', 'font-style': 'italic', 'padding-left': '20px', 'padding-top': '10px'}
                    ),
                ]),
            ]),
        ]),

        # --- Top Level Tab: Advanced Stats ---
        dcc.Tab(label='Advanced Stats', className='custom-top-tab', selected_className='custom-top-tab-selected', children=[
                # --- Nested Tabs for parent In-Season Tools tab
                dcc.Tabs(className='nested-tabs-container', children=[
                    # --- Weekly Efficiency Tab ---
                    dcc.Tab(label='Fantasy Efficiency', value='efficiency', className='custom-nested-tab',
                            selected_className='custom-nested-tab-selected', children=[
                            html.Br(),
                            html.Div([
                                html.Label("Position: ", style={'margin-right': '20px'}),
                                dcc.RadioItems(
                                    id='position-efficiency-selection',
                                    options=[
                                        {'label': 'QB', 'value': 'QB'},
                                        {'label': 'RB', 'value': 'RB'},
                                        {'label': 'WR', 'value': 'WR'},
                                        {'label': 'TE', 'value': 'TE'}
                                    ],
                                    value='RB',  # Default value
                                    inline=True,
                                    labelStyle={'margin-right': '20px'}
                                ),
                            ], style={'display': 'flex', 'align-items': 'center', 'padding': '0px 25px'}),
                            html.Br(),
                            dcc.Loading(
                                id='loading-efficiency-chart',
                                type='circle',
                                children=dcc.Graph(id='efficiency-chart')
                            ),
                            html.Hr(),
                            dcc.Markdown("""
        This chart plots a player's actual fantasy points vs. their expected points based on usage.
        *   **Players above the line** were efficient with their fantasy production and scored more than expected (possible regression candidate).
        *   **Players below the line** were inefficient and scored less than expected.
    """, style={'color': 'grey', 'font-style': 'italic', 'padding-left': '25px', 'padding-top': '10px'})
                        ]),
                    # --- Receiving Share tab ---
                    dcc.Tab(label='Receiving Share', className='custom-nested-tab',
                            selected_className='custom-nested-tab-selected', children=[
                            html.Br(),

                            dcc.Loading(
                                id='loading-share-chart',
                                type='circle',
                                children=dcc.Graph(id='share-chart')
                            ),
                            html.Hr(),
                            dcc.Markdown("""
                            *Target Share* refers to how often that player is targeted with respect to the rest of the receivers on their team.
                            *Air Yard Share* refers to the total number of yards the ball traveled on those targets (including incompletions) with respect to the rest of their team. 
                            
                            **Note:** Use this chart to understand how much opportunity a receiver has been given throughout the season. Whether they actually convert this opportunity to produce fantasy points is not represented here.
                            
                            **Tooltip**: WOPR is the Weighted Opportunity Rating. It combines both target and air yard share into a single metric to measure receiving opportunity. The higher this number, the more of a focal point this player is to their offense.
                            """,
                            style={'color': 'grey', 'font-style': 'italic', 'padding-left': '25px','padding-top': '10px'})
                ]),
                    # --- Receiver Separation tab ---
                    dcc.Tab(label='Receiver Separation', className='custom-nested-tab',
                            selected_className='custom-nested-tab-selected', children=[
                            html.Br(),

                            dcc.Loading(
                                id='loading-separation-chart',
                                type='circle',
                                children=dcc.Graph(id='separation-chart')
                            ),
                            html.Hr(),
                            dcc.Markdown("""
                            This chart plots a receiver's ability to get open against the respect defenses give them.

                            *   **Cushion**: How far off the line of scrimmage a covering defender plays.
                            *   **Separation**: How open a receiver is when the pass arrives. 
                            
                            **Note:** The size of the bubble indicates the number of targets. The bigger the bubble, the more accurate its placement in the chart.
                            """,
                            style={'color': 'grey', 'font-style': 'italic', 'padding-left': '25px','padding-top': '10px'})
                ]),
                    # --- Stacked Box tab ---
                    dcc.Tab(label='Rushing Vs. Stacked Box', className='custom-nested-tab',
                            selected_className='custom-nested-tab-selected', children=[
                            html.Br(),

                            dcc.Loading(
                                id='loading-box-chart',
                                type='circle',
                                children=dcc.Graph(id='box-chart')
                            ),
                            html.Hr(),
                            dcc.Markdown("""
                            This chart plots a running back's efficiency against the difficulty of their situation.
                
                            *   **Rush Yards over Expected per Attempt**: Measures how many more yards a player gains compared to an average back in the exact same situation (down, distance, defensive alignment, etc.). This is a measure of pure talent and elusiveness.
                            *   **Stacked Box Percentage**: Shows how often a player runs against 8 or more defenders in the box. This is a measure of the difficulty of their role.
                            
                            **Note:** The size of the bubble indicates the number of rushing attempts. The bigger the bubble, the more accurate its placement in the chart.
                            """,
                            style={'color': 'grey', 'font-style': 'italic', 'padding-left': '25px','padding-top': '10px'})
                ]),
                    # --- QB Aggressiveness tab ---
                    dcc.Tab(label='QB Aggressiveness', className='custom-nested-tab',
                            selected_className='custom-nested-tab-selected', children=[
                            html.Br(),

                            dcc.Loading(
                                id='loading-qb-chart',
                                type='circle',
                                children=dcc.Graph(id='qb-chart')
                            ),
                            html.Hr(),
                            dcc.Markdown("""
                            This chart plots a quarterback's efficiency against how aggressive they are.

                            *   **Aggressiveness**: The percentage of a QB's throws that are into tight windows (defender within 1 yard).
                            *   **CPOE**: Completion Percentage Above Expectation. A measure of pure accuracy against the difficulty of the throw.
                            
                            **Note:** The size of the bubble indicates the number of passing attempts. The bigger the bubble, the more accurate its placement in the chart.
                            """,
                            style={'color': 'grey', 'font-style': 'italic', 'padding-left': '25px','padding-top': '10px'})
                ]),
            ]),
        ]),
    ]),
])


# --- Callbacks to Enable/Disable League-Specific Controls ---
@app.callback(
    [Output('owner-name-dropdown', 'options'),
     Output('owner-name-dropdown', 'disabled'),
     Output('show-taken-draft-checkbox', 'options'), # Control options to disable
     Output('show-taken-proj-checkbox', 'options')],  # Control options to disable
    [Input('league-id-input', 'value')]
)
def update_owner_dropdown(league_id):
    """
    Populates the owner ID dropdown based on the entered league ID. If no league_id provided,
    disable the dropdown along with the show_taken checkboxes.

    This callback is triggered whenever the 'league-id-input' value changes.
    It fetches the league's user data and formats it for the dropdown.
    """
    # Prevent callback from firing with an empty league ID.
    if league_id:
        league_df = get_league_info(league_id)
        owner_options = (
            league_df.select(pl.col('owner_name').alias('label'),
                             pl.col('owner_name').alias('value')).to_dicts())
        checkbox_options = [{'label': 'Show Taken Players', 'value': 'show_taken'}] # Default control options to enable.
        # Enable the controls
        return owner_options, False, checkbox_options, checkbox_options
    # If no league_id, return empty owner options, disable owner dropdown, and disable checkboxes
    return [], True, [], []


# --- Callback to fetch and store league-specific data ---
@app.callback(
    Output('league-info-store', 'data'),
    Input('league-id-input', 'value')
)
def update_league_store(league_id):
    """
    Fetches league data from the Sleeper API when the league_id changes and stores it as JSON in a dcc.Store.
    """
    if not league_id:
        return None  # Return None if no ID is provided

    league_df = get_league_info(league_id)
    return league_df.write_json()


# --- Master Callback to Compute and Store Full Board Data ---
@app.callback(
    [Output('draft-positional-board-store', 'data'),
     Output('draft-overall-board-store', 'data'),
     Output('weekly-board-store', 'data')],
    [Input('league-info-store', 'data')],  # Triggered when league data is ready
    # prevent_initial_call=False  # Ensure this runs on page load
)
def update_board_stores(league_data):
    """
    This master callback runs the expensive computations once and stores the results.
    It's triggered when the league data becomes available.
    """
    league_df = pl.read_json(io.StringIO(league_data)) if league_data else None

    # --- Create and store the full positional draft board ---
    draft_positional_board_df = create_board(league_df=league_df, draft=True, positional=True)
    draft_positional_data = draft_positional_board_df.write_json()

    # --- Create and store the full overall draft board ---
    draft_overall_board_df = create_board(league_df=league_df, draft=True, positional=False)
    draft_overall_data = draft_overall_board_df.write_json()

    # --- Create and store the full weekly board (all positions) ---
    weekly_board_df = create_board(league_df=league_df, draft=False, positional=True) # positional is ignored
    weekly_data = weekly_board_df.write_json()

    return draft_positional_data, draft_overall_data, weekly_data


# --- Callback to Update Draft Board Table ---
@app.callback(
    [
        Output('draft-table', 'data'),
        Output('draft-table', 'columns'),
        Output('draft-last-update', 'children'),
        Output('draft-table', 'style_data_conditional')
    ],
    [
        Input('owner-name-dropdown', 'value'),
        Input('draft-positional-board-store', 'data'),
        Input('draft-overall-board-store', 'data'),
        Input('position-draft-selection', 'value'),
        Input('show-taken-draft-checkbox', 'value')
    ],
)
def update_draft_table(owner_name, draft_positional_data, draft_overall_data, position, show_taken_value):
    """
    Updates the dynasty draft board table based on user selections.

    This is a "consumer" callback. It reads pre-computed data from the dcc.Store
    and performs fast, in-memory filtering.
    """
    # Ensure all necessary inputs are provided before attempting to fetch data.
    if not all([draft_positional_data, draft_overall_data, position]):
        return [], [], "", []

    if position == 'Overall':
        # Load the full overall board from the store
        board_df = pl.read_json(io.StringIO(draft_overall_data))
    else:
        # Load the full board from the store
        board_df = pl.read_json(io.StringIO(draft_positional_data))

        # Filter for the selected position
        board_df = board_df.filter(pl.col('pos') == position)

    # The checklist's value is a list. It's not empty if the box is checked.
    show_taken_flag = bool(show_taken_value)

    # Apply roster filtering if requested
    if not show_taken_flag and owner_name and 'Owner' in board_df.columns and board_df['Owner'][0] != 'N/A':
        board_df = board_df.filter((pl.col('Owner') == owner_name) | (pl.col('Owner') == 'Free Agent'))

    # Get scrape_date to represent the last update of the data.
    last_update_text = ""
    if not board_df.is_empty() and 'scrape_date' in board_df.columns:
        # Get the date from the first row and format it
        scrape_date = board_df['scrape_date'][0]
        last_update_text = f"Last Update: {scrape_date}"

    # --- Generate Conditional Styling & Final Columns ---
    styles = []
    columns_to_drop = ['fantasypros_id', 'scrape_date', 'pos']

    # Only apply ownership styling and show Owner column if a league is active
    if 'Owner' in board_df.columns and board_df['Owner'][0] != 'N/A':
        if owner_name:
            styles.append({
                'if': {'filter_query': '{Owner} = "' + owner_name + '"'},
                'backgroundColor': 'rgba(0, 123, 255, 0.15)',
            })
        styles.append({
            'if': {'filter_query': '{Owner} = "Free Agent"'},
            'backgroundColor': 'rgba(40, 167, 69, 0.15)',
        })
    else:
        # If no league, hide the 'Owner' column
        columns_to_drop.append('Owner')

    # Format the DataFrame for the Dash DataTable
    board_df = board_df.drop(columns_to_drop)
    columns = [{"name": i, "id": i} for i in board_df.columns]
    data = board_df.to_dicts()

    return data, columns, last_update_text, styles


# --- Callback to Update Weekly Projections Table ---
@app.callback(
    [
        Output('proj-table', 'data'),
        Output('proj-table', 'columns'),
        Output('proj-last-update', 'children'),
        Output('proj-table', 'style_data_conditional')
    ],
    [
        Input('owner-name-dropdown', 'value'),
        Input('weekly-board-store', 'data'),
        Input('position-proj-selection', 'value'),
        Input('show-taken-proj-checkbox', 'value')
    ],
)
def update_proj_table(owner_name, weekly_data, position, show_taken_value):
    """
    Updates the weekly projections table based on user selections.

    This is a "consumer" callback. It reads pre-computed data from the dcc.Store
    and performs fast, in-memory filtering.
    """
    # Ensure all necessary inputs are provided before attempting to fetch data.
    if not all([weekly_data, position]):
        return [], [], "", [] # Return empty list for styles

    # Load the full board from the store
    board_df = pl.read_json(io.StringIO(weekly_data))

    # Filter for the selected position
    board_df = board_df.filter(pl.col('pos') == position)

    # The checklist's value is a list. It's not empty if the box is checked.
    show_taken_flag = bool(show_taken_value)

    # Apply roster filtering if requested
    if not show_taken_flag and owner_name and 'Owner' in board_df.columns and board_df['Owner'][0] != 'N/A':
        board_df = board_df.filter((pl.col('Owner') == owner_name) | (pl.col('Owner') == 'Free Agent'))

    # Get scrape_date to represent the last update of the data.
    last_update_text = ""
    if not board_df.is_empty() and 'scrape_date' in board_df.columns:
        # Get the date from the first row and format it
        scrape_date = board_df['scrape_date'][0]
        last_update_text = f"Last Update: {scrape_date}"

    # --- Generate Conditional Styling & Final Columns ---
    styles = []
    columns_to_drop = ['fantasypros_id', 'scrape_date', 'pos']

    # Only apply ownership styling and show Owner column if a league is active
    if 'Owner' in board_df.columns and board_df['Owner'][0] != 'N/A':
        if owner_name:
            styles.append({
                'if': {'filter_query': '{Owner} = "' + owner_name + '"'},
                'backgroundColor': 'rgba(0, 123, 255, 0.15)',
            })
        styles.append({
            'if': {'filter_query': '{Owner} = "Free Agent"'},
            'backgroundColor': 'rgba(40, 167, 69, 0.15)',
        })
    else:
        # If no league, hide the 'Owner' column
        columns_to_drop.append('Owner')

    # Format the DataFrame for the Dash DataTable
    board_df = board_df.drop(columns_to_drop)
    columns = [{"name": i, "id": i} for i in board_df.columns]
    data = board_df.to_dicts()

    return data, columns, last_update_text, styles


# --- Callback to Update Draft Tiers Chart ---
@app.callback(
    Output('draft-tier-chart-graph', 'figure'),
    [
        Input('draft-positional-board-store', 'data'),
        Input('position-draft-tier-selection', 'value'),
        Input('owner-name-dropdown', 'value') # Add owner name as an Input
    ]
)
def update_draft_tier_chart(draft_data, position, owner_name):
    """
    Generates and displays the player tier visualization.

    This callback reads the pre-computed draft board data, filters it,
    calculates tiers, and then creates the chart.
    """

    n_players = {'QB': 32, 'RB': 64, 'WR': 96, 'TE': 32}  # Number of players to cluster by position.
    tier_range = {'QB': range(8, 10 + 1), 'RB': range(10, 12 + 1),  # Range for number of clusters to test using BIC
                  'WR': range(12, 14 + 1), 'TE': range(8, 10 + 1)}

    if not draft_data or not position:
        return dash.no_update

    # Load and filter the main board data
    board_df = pl.read_json(io.StringIO(draft_data))
    position_df = board_df.filter(pl.col('pos') == position)

    # Apply the tiering algorithm
    tiered_df = create_tiers(
        position_df,
        tier_range=tier_range[position],
        n_players=n_players[position]
    )

    # Generate the Plotly figure
    fig = create_tier_chart(tiered_df, user_name=owner_name)

    return fig


# --- Callback to Update Weekly Tiers Chart ---
@app.callback(
    Output('weekly-tier-chart-graph', 'figure'),
    [
        Input('weekly-board-store', 'data'),
        Input('position-weekly-tier-selection', 'value'),
        Input('owner-name-dropdown', 'value')
    ]
)
def update_weekly_tier_chart(weekly_data, position, owner_name):
    """
    Generates and displays the player tier visualization.

    This callback reads the pre-computed weekly projections data, filters it,
    calculates tiers, and then creates the chart.
    """
    n_players = {'QB': 24, 'RB': 40, 'WR': 60, 'TE': 24}  # Number of players to cluster by position.
    tier_range = {'QB': range(6, 8 + 1), 'RB': range(8, 10 + 1),  # Range for number of clusters to test using BIC
                  'WR': range(10, 12 + 1), 'TE': range(6, 8 + 1)}

    if not weekly_data or not position:
        return dash.no_update

    # Load and filter the main board data
    board_df = pl.read_json(io.StringIO(weekly_data))
    position_df = board_df.filter(pl.col('pos') == position)

    # Apply the tiering algorithm
    tiered_df = create_tiers(
        position_df,
        tier_range=tier_range[position],
        n_players=n_players[position])

    # Generate the Plotly figure
    fig = create_tier_chart(tiered_df, user_name=owner_name)

    return fig


# --- Callback to Update Dynasty Trade Value Tables ---
@app.callback(
    [
        Output('trade-value-table-qb', 'data'), Output('trade-value-table-qb', 'columns'),
        Output('trade-value-table-rb', 'data'), Output('trade-value-table-rb', 'columns'),
        Output('trade-value-table-wr', 'data'), Output('trade-value-table-wr', 'columns'),
        Output('trade-value-table-te', 'data'), Output('trade-value-table-te', 'columns'),
        Output('trade-value-table-qb', 'style_data_conditional'),
        Output('trade-value-table-rb', 'style_data_conditional'),
        Output('trade-value-table-wr', 'style_data_conditional'),
        Output('trade-value-table-te', 'style_data_conditional')
    ],
    [
        Input('draft-overall-board-store', 'data'),
        Input('owner-name-dropdown', 'value')
    ],
    [State('league-info-store', 'data')]
)
def update_trade_value_tables(draft_data, owner_name, league_data):
    """
    Calculates trade values and populates the four positional tables.
    """
    if not draft_data:
        # Return empty data for all 8 outputs if the store is empty + the 4 conditional styles
        return [[] for _ in range(12)]

    # Load the full board from the store
    board_df = pl.read_json(io.StringIO(draft_data))

    # Get trade values
    values_df = create_trade_values(board_df, inseason=False)

    # --- Generate Conditional Styling ---
    styles = []
    if league_data and owner_name:
        styles.append({
            'if': {'filter_query': '{Owner} = "' + owner_name + '"'},
            'backgroundColor': 'rgba(0, 123, 255, 0.15)',
        })

    # Helper function to prepare data for positional tables
    def prep_value_tables(pos: str):
        pos_values_df = values_df.filter(pl.col('pos') == pos).sort('Value', descending=True)

        # Define the columns to display in the table
        display_cols = ['Player', 'Age', 'Value']
        # Select the final columns for display
        table_df = pos_values_df.select(display_cols)

        columns = [{"name": i, "id": i} for i in table_df.columns]
        # Pass the full data with the 'Owner' column (if it exists) for the filter_query to work
        data = pos_values_df.to_dicts()
        return data, columns

    qb_data, qb_columns = prep_value_tables('QB')
    rb_data, rb_columns = prep_value_tables('RB')
    wr_data, wr_columns = prep_value_tables('WR')
    te_data, te_columns = prep_value_tables('TE')

    return (qb_data, qb_columns, rb_data, rb_columns, wr_data, wr_columns,
            te_data, te_columns, styles, styles, styles, styles)


# --- Callback to Update Efficiency Chart ---
@app.callback(
    Output('efficiency-chart', 'figure'),
    [
        Input('owner-name-dropdown', 'value'),
        Input('position-efficiency-selection', 'value')
    ],
    [State('league-info-store', 'data')]
)
def update_efficiency_chart(owner_name, position, league_data):
    """
    Computes player efficiency and generates the scatter plot visualization.
    """
    if not position:
        return go.Figure()

    league_df = pl.read_json(io.StringIO(league_data)) if league_data else None
    efficiency_df = compute_efficiency(league_df=league_df)

    if efficiency_df.is_empty():
        return go.Figure()

    # Filter by the selected position
    pos_df = efficiency_df.filter(pl.col('pos') == position)

    # Generate the Plotly figure, passing the owner_name for highlighting
    return create_efficiency_chart(pos_df, user_name=owner_name)


# --- Callback to Update Receiving Share Chart ---
@app.callback(
    Output('share-chart', 'figure'),
    [
        Input('owner-name-dropdown', 'value')
    ],
    [State('league-info-store', 'data')]
)
def update_share_chart(owner_name, league_data):
    """
    Computes full-season receiving share data and generates the scatter plot visualization.
    """
    # Load in receiving share data
    league_df = pl.read_json(io.StringIO(league_data)) if league_data else None
    share_df = receiving_share(league_df=league_df)

    if share_df.is_empty():
        return go.Figure()

    # Generate the Plotly figure, passing the owner_name for highlighting
    return create_share_chart(share_df, user_name=owner_name)


# --- Callback to Update Stacked Box Chart ---
@app.callback(
    Output('box-chart', 'figure'),
    [
        Input('owner-name-dropdown', 'value')
    ],
    [State('league-info-store', 'data')]
)
def update_box_chart(owner_name, league_data):
    """
    Computes full-season rushing efficiency vs stacked box data and generates the scatter plot visualization.
    """
    # Load in stacked box data
    league_df = pl.read_json(io.StringIO(league_data)) if league_data else None
    box_df = stacked_box_efficiency(league_df=league_df)

    if box_df.is_empty():
        return go.Figure()

    # Generate the Plotly figure, passing the owner_name for highlighting
    return create_box_chart(box_df, user_name=owner_name)


# --- Callback to Update Receiver Separation Chart ---
@app.callback(
    Output('separation-chart', 'figure'),
    [
        Input('owner-name-dropdown', 'value')
    ],
    [State('league-info-store', 'data')]
)
def update_separation_chart(owner_name, league_data):
    """
    Computes receiver separation data and generates the scatter plot visualization.
    """
    # Load in separation data
    league_df = pl.read_json(io.StringIO(league_data)) if league_data else None
    separation_df = receiver_separation(league_df=league_df)

    if separation_df.is_empty():
        return go.Figure()

    # Generate the Plotly figure, passing the owner_name for highlighting
    return create_separation_chart(separation_df, user_name=owner_name)


# --- Callback to Update QB Aggressiveness Chart ---
@app.callback(
    Output('qb-chart', 'figure'),
    [
        Input('owner-name-dropdown', 'value')
    ],
    [State('league-info-store', 'data')]
)
def update_aggressiveness_chart(owner_name, league_data):
    """
    Computes QB Aggressiveness data and generates the scatter plot visualization.
    """
    # Load in QB aggressiveness data
    league_df = pl.read_json(io.StringIO(league_data)) if league_data else None
    qb_df = qb_aggressiveness(league_df=league_df)

    if qb_df.is_empty():
        return go.Figure()

    # Generate the Plotly figure, passing the owner_name for highlighting
    return create_qb_playstyle_chart(qb_df, user_name=owner_name)


# --- Run the Application ---
# This block allows the script to be run directly to start the development server.
if __name__ == '__main__':
    app.run(debug=True)
