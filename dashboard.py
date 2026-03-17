"""
This module defines the layout and callback logic for the Sleeper Dynasty Assistant dashboard.
"""

# --- Backend Imports ---
import logging
import polars as pl
import io
import tempfile

# --- Dashboard Imports ---
import dash
from dash import dcc, html, dash_table
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go

# --- Import Helper Functions ---
from src.boards import create_board
from src.league import get_league_info
from src.tiers import create_tiers
from src.trade import create_trade_values
from src.team import analyze_team
from src.advanced_stats import (compute_efficiency, receiving_share, rushing_share)
from src.visualizations import (create_tier_chart, create_efficiency_chart,
                                create_rec_share_chart, create_rush_share_chart,
                                create_team_radar_chart)

# --- Configure Logging ---
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# --- Configure nflreadpy Cache ---
from pathlib import Path
from nflreadpy.config import update_config

# Use the system's temporary directory for caching to ensure write access in cloud environments
cache_dir = Path(tempfile.gettempdir()) / "nflreadpy_cache"
update_config(cache_mode="filesystem", cache_dir=cache_dir, verbose=True, cache_duration=43200)

# Initialize the Dash application
app = dash.Dash(__name__, suppress_callback_exceptions=False, external_stylesheets=[dbc.themes.BOOTSTRAP])

# Server variable
server = app.server

# --- App Layout ---
app.layout = dbc.Container([
    # --- Data Stores ---
    # These hidden components store the results of expensive computations.
    dcc.Store(id='draft-positional-board-store'),
    dcc.Store(id='draft-overall-board-store'),
    dcc.Store(id='weekly-board-store'),
    dcc.Store(id='league-info-store'),

    # --- Header Section ---
    dbc.Row([
        dbc.Col(html.H1("Sleeper Dynasty Assistant"), width="auto"),
        dbc.Col(html.A("Github", href="https://github.com/awguzman/Sleeper-Dynasty-Assistant", target="_blank"),
                width="auto", className="d-flex align-items-center")
    ], justify="between", className="my-3"),

    # --- Global Controls ---
    dbc.Row([
        dbc.Col(dbc.InputGroup([
            dbc.InputGroupText("Sleeper League ID"),
            dbc.Input(id="league-id-input", placeholder="e.g., 992016434344030208", type="text"),
            dbc.Button("Load League", id="load-league-button", color="primary", n_clicks=0),
        ]), md=6),
        dbc.Col(dbc.InputGroup([
            dbc.InputGroupText("Select Owner"),
            dbc.Select(id='owner-name-dropdown', placeholder='Your username', disabled=True),
        ]), md=6),
    ], className="mb-3"),

    # --- Alerts ---
    dbc.Row([
        dbc.Col([
            dbc.Alert(id='league-id-alert', is_open=False, duration=4000),
            dbc.Alert(
                "This page has limited functionality until after the NFL draft at the end of April.",
                id='offseason-alert',
                color='warning',
                is_open=False,
                dismissable=True
            )
        ], width=12)
    ]),

    # --- Main Tabbed Interface ---
    dbc.Tabs([
        # --- Overview Tab ---
        dbc.Tab(label='Overview', children=[
            dbc.Row([
                # Left Column: Roster
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader(html.H4(id='overview-roster-title', children="Roster", className="m-0")),
                        dbc.CardBody([
                            dcc.Loading(type='circle', children=html.Div(id='overview-roster-list'))
                        ])
                    ], className="h-100")
                ], md=6),
                # Right Column: Strength
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader(html.H4("Positional Strength", className="m-0")),
                        dbc.CardBody([
                            dcc.Loading(type='circle', children=html.Div(id='overview-strength-list')),
                            dcc.Loading(type='circle', children=dcc.Graph(id='overview-radar-chart'))
                        ])
                    ], className="h-100")
                ], md=6)
            ], className="mt-3"),
            html.Hr(),
            dcc.Markdown("""
            **Value** is a metric calculated based on a player's dynasty Expert Consensus Ranking (ECR). 
            It represents a normalized score where higher values indicate greater long-term asset value in a dynasty league context.
            """, className="text-muted fst-italic mt-3")
        ]),
        # --- Trade Values tab ---
        dbc.Tab(label='Trade Values', children=[
            dbc.Row([
                # QB Table
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Quarterback", className="fw-bold text-center"),
                        dbc.CardBody(
                            dcc.Loading(type='circle', children=dash_table.DataTable(
                                id='trade-value-table-qb',
                                style_table={'height': '600px', 'overflowY': 'auto'},
                                style_header={'fontWeight': 'bold', 'borderBottom': '2px solid #dee2e6'},
                                style_cell={'textAlign': 'left', 'padding': '10px'},
                                style_cell_conditional=[
                                    {'if': {'column_id': 'Player'}, 'width': '50%'},
                                    {'if': {'column_id': ['Age', 'Value']}, 'width': '25%'}
                                ],
                                style_as_list_view=True,
                            ))
                        )
                    ])
                ], md=3),
                # RB Table
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Running Back", className="fw-bold text-center"),
                        dbc.CardBody(
                            dcc.Loading(type='circle', children=dash_table.DataTable(
                                id='trade-value-table-rb',
                                style_table={'height': '600px', 'overflowY': 'auto'},
                                style_header={'fontWeight': 'bold', 'borderBottom': '2px solid #dee2e6'},
                                style_cell={'textAlign': 'left', 'padding': '10px'},
                                style_cell_conditional=[
                                    {'if': {'column_id': 'Player'}, 'width': '50%'},
                                    {'if': {'column_id': ['Age', 'Value']}, 'width': '25%'}
                                ],
                                style_as_list_view=True,
                            ))
                        )
                    ])
                ], md=3),
                # WR Table
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Wide Receiver", className="fw-bold text-center"),
                        dbc.CardBody(
                            dcc.Loading(type='circle', children=dash_table.DataTable(
                                id='trade-value-table-wr',
                                style_table={'height': '600px', 'overflowY': 'auto'},
                                style_header={'fontWeight': 'bold', 'borderBottom': '2px solid #dee2e6'},
                                style_cell={'textAlign': 'left', 'padding': '10px'},
                                style_cell_conditional=[
                                    {'if': {'column_id': 'Player'}, 'width': '50%'},
                                    {'if': {'column_id': ['Age', 'Value']}, 'width': '25%'}
                                ],
                                style_as_list_view=True,
                            ))
                        )
                    ])
                ], md=3),
                # TE Table
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Tight End", className="fw-bold text-center"),
                        dbc.CardBody(
                            dcc.Loading(type='circle', children=dash_table.DataTable(
                                id='trade-value-table-te',
                                style_table={'height': '600px', 'overflowY': 'auto'},
                                style_header={'fontWeight': 'bold', 'borderBottom': '2px solid #dee2e6'},
                                style_cell={'textAlign': 'left', 'padding': '10px'},
                                style_cell_conditional=[
                                    {'if': {'column_id': 'Player'}, 'width': '50%'},
                                    {'if': {'column_id': ['Age', 'Value']}, 'width': '25%'}
                                ],
                                style_as_list_view=True,
                            ))
                        )
                    ])
                ], md=3),
            ], className="mt-3"),
            html.Hr(),
            dcc.Markdown("""
            Trade values are based on overall dynasty ECR values. They will (possibly over)emphasize long term value
            over short-term gain.
            """, className="text-muted fst-italic mt-3")
        ]),
        # --- Draft Tab ---
        dbc.Tab(label='Draft Board', children=[
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Draft Board"),
                        dbc.CardBody([
                            dbc.Row([
                                dbc.Col(dbc.RadioItems(
                                    id='position-draft-selection',
                                    options=[
                                        {'label': 'Overall', 'value': 'Overall'},
                                        {'label': 'Quarterback', 'value': 'QB'},
                                        {'label': 'Running Back', 'value': 'RB'},
                                        {'label': 'Wide Receiver', 'value': 'WR'},
                                        {'label': 'Tight End', 'value': 'TE'},
                                    ],
                                    value='Overall',
                                    inline=True,
                                    labelClassName="me-3"
                                ), width="auto"),
                                dbc.Col(dbc.Checklist(
                                    id='show-taken-draft-checkbox',
                                    options=[{'label': 'Show Taken Players', 'value': 'show_taken'}],
                                    value=[],
                                ), width="auto"),
                            ], justify="between", align="center", className="my-3"),
                            dcc.Loading(
                                id='loading-draft-table',
                                type='circle',
                                children=[
                                    html.Div(id='draft-last-update', className="text-end text-muted fst-italic mb-1"),
                                    dash_table.DataTable(
                                        id='draft-table',
                                        style_data_conditional=[],
                                        style_table={'overflowX': 'auto'},
                                        style_header={'fontWeight': 'bold', 'borderBottom': '2px solid #dee2e6'},
                                        style_cell={'textAlign': 'left', 'padding': '10px', 'whiteSpace': 'normal', 'height': 'auto'},
                                        style_cell_conditional=[
                                            {'if': {'column_id': ['Player', 'Owner']}, 'width': '180px', 'minWidth': '180px', 'maxWidth': '250px'},
                                            {'if': {'column_id': ['Pos', 'Team', 'ECR', 'Best', 'Worst', 'Std', 'Age', 'Bye']}, 'width': '80px', 'minWidth': '80px', 'maxWidth': '80px'}
                                        ],
                                        style_as_list_view=True,
                                    )
                                ]
                            ),
                            html.Hr(),
                            dcc.Markdown("""
                            Note: This table does not take into consideration in-season performance. It should be considered 
                            outdated following the first week of play.
                        
                            *   **ECR**: Expert Consensus Ranking. The (weighted) average rank given to a player from all experts surveyed by FantasyPros.
                            *   **Std**: Standard deviation of rankings given to a player from all experts. Smaller values mean higher agreement among experts. 
                        
                            """, className="text-muted fst-italic mt-3")
                        ])
                    ], className="mt-3")
                ], md=6),
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Draft Tiers"),
                        dbc.CardBody([
                            dbc.RadioItems(
                                id='position-draft-tier-selection',
                                options=[
                                    {'label': 'Quarterback', 'value': 'QB'},
                                    {'label': 'Running Back', 'value': 'RB'},
                                    {'label': 'Wide Receiver', 'value': 'WR'},
                                    {'label': 'Tight End', 'value': 'TE'},
                                ],
                                value='QB',
                                inline=True,
                                labelClassName="me-3",
                                className="my-3"
                            ),
                            dcc.Loading(id='loading-draft-tier-chart', type='circle', children=dcc.Graph(id='draft-tier-chart-graph')),
                            html.Hr(),
                            dcc.Markdown("""
                            Uses a Gaussian Mixture Model (GMM) together with Bayesian Information Criterion (BIC) to dynamically 
                            cluster players into statistically similar tiers. This should be viewed as a measure of how similar any two 
                            players are ranked by FantasyPros.The left most end of a players error bar measures the most optimistic 
                            expert ranking, likewise, the right most end measures the least optimistic ranking.
                        
                            Inspired by analysis of Boris Chen, see www.borischen.co
                            
                            Note: This does not take into consideration in-season performance. It should be considered 
                            outdated following the first week of play.
                            """, className="text-muted fst-italic mt-3")
                        ])
                    ], className="mt-3")
                ], md=6)
            ])
        ]),
        # --- Weekly Tab ---
        dbc.Tab(label='Weekly Projections', children=[
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Weekly Rankings"),
                        dbc.CardBody([
                            dbc.Row([
                                dbc.Col(dbc.RadioItems(
                                    id='position-proj-selection',
                                    options=[
                                        {'label': 'Quarterback', 'value': 'QB'},
                                        {'label': 'Running Back', 'value': 'RB'},
                                        {'label': 'Wide Receiver', 'value': 'WR'},
                                        {'label': 'Tight End', 'value': 'TE'},
                                    ],
                                    value='QB',
                                    inline=True,
                                    labelClassName="me-3"
                                ), width="auto"),
                                dbc.Col(dbc.Checklist(
                                    id='show-taken-proj-checkbox',
                                    options=[{'label': 'Show Taken Players', 'value': 'show_taken'}],
                                    value=[],
                                ), width="auto"),
                            ], justify="between", align="center", className="my-3"),

                            dcc.Loading(
                                id='loading-proj-table',
                                type='circle',
                                children=[
                                    html.Div(id='proj-last-update', className="text-end text-muted fst-italic mb-1"),
                                    dash_table.DataTable(
                                        id='proj-table',
                                        style_data_conditional=[],
                                        style_table={'overflowX': 'auto'},
                                        style_header={'fontWeight': 'bold', 'borderBottom': '2px solid #dee2e6'},
                                        style_cell={'textAlign': 'left', 'padding': '10px', 'whiteSpace': 'normal', 'height': 'auto'},
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
                                        ],
                                        style_as_list_view=True,
                                    )
                                ]
                            ),

                            html.Hr(),
                            dcc.Markdown("""
                            Note: "Last Update" refers to the last update of data provided by FantasyPros. This application has no 
                            control over the frequency of such updates.
                        
                            *   **ECR**: Expert Consensus Ranking. The (weighted) average rank given to a player from all experts surveyed by FantasyPros.
                            *   **Std**: Standard deviation of rankings given to a player from all experts. Smaller values mean higher agreement among experts. 
                        
                            """, className="text-muted fst-italic mt-3")
                        ])
                    ], className="mt-3")
                ], md=6),
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Weekly Tiers"),
                        dbc.CardBody([
                            dbc.RadioItems(
                                id='position-weekly-tier-selection',
                                options=[
                                    {'label': 'Quarterback', 'value': 'QB'},
                                    {'label': 'Running Back', 'value': 'RB'},
                                    {'label': 'Wide Receiver', 'value': 'WR'},
                                    {'label': 'Tight End', 'value': 'TE'},
                                ],
                                value='QB',
                                inline=True,
                                labelClassName="me-3",
                                className="my-3"
                            ),
                            dcc.Loading(id='loading-weekly-tier-chart', type='circle',
                                        children=dcc.Graph(id='weekly-tier-chart-graph')),
                            html.Hr(),
                            dcc.Markdown("""
                            Uses a Gaussian Mixture Model (GMM) together with Bayesian Information Criterion (BIC) to dynamically 
                            cluster players into statistically similar tiers. This should be viewed as a measure of how similar any two 
                            players are ranked by FantasyPros. The left most end of a players error bar measures the most optimistic 
                            expert ranking, likewise, the right most end measures the least optimistic ranking.
                        
                            Inspired by analysis of Boris Chen, see www.borischen.co
                            """, className="text-muted fst-italic mt-3")
                        ])
                    ], className="mt-3")
                ], md=6)
            ])
        ]),
        # --- Advanced Stats Tab ---
        dbc.Tab(label='Advanced Stats', children=[
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Fantasy Efficiency"),
                        dbc.CardBody([
                            dbc.RadioItems(
                                id='position-efficiency-selection',
                                options=[
                                    {'label': 'QB', 'value': 'QB'},
                                    {'label': 'RB', 'value': 'RB'},
                                    {'label': 'WR', 'value': 'WR'},
                                    {'label': 'TE', 'value': 'TE'}
                                ],
                                value='RB',
                                inline=True,
                                labelClassName="me-3",
                                className="my-3"
                            ),
                            dcc.Loading(id='loading-efficiency-chart', type='circle',
                                        children=dcc.Graph(id='efficiency-chart')),
                            html.Hr(),
                            dcc.Markdown("""
                                This chart plots a player's actual fantasy points versus their expected points based on 
                                their usage throughout the season.
                                
                                The dashed line represents the expected position of players based on historical data. 
                                Due to the way that these probabilities are calculated and the randomness of football, 
                                one should not expect most players lie below this line. Any player above it should be 
                                expected to regress throughout the season/next season.
                            """, className="text-muted fst-italic mt-3")
                        ])
                    ], className="mt-3")
                ], width=12)
            ]),
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Receiving Share"),
                        dbc.CardBody([
                            dcc.Loading(id='loading-rec-share-chart', type='circle',
                                        children=dcc.Graph(id='rec-share-chart'), className="my-3"),
                            html.Hr(),
                            dcc.Markdown("""
                            This chart plots the quality of a players target share on their team versus their 
                            receiving yard share.
                            
                            **Weighted Opportunity Rating (WOPR)** is a metric measuring the not only how many targets a 
                            player receives but also the quality of those targets (WOPR = (Target Share) + 0.7(Air Yard Share))
                            
                            **Receiving Yard Share** refers to a players share of actual receiving yards with respect to 
                            the rest of the team. This measures the actual production of the player.
                            """,
                                         className="text-muted fst-italic mt-3")
                        ])
                    ], className="mt-3")
                ], width=12)
            ]),
            dbc.Row([
                dbc.Col([
                    dbc.Card([
                        dbc.CardHeader("Rushing Share"),
                        dbc.CardBody([
                            dcc.Loading(id='loading-rush-share-chart', type='circle',
                                        children=dcc.Graph(id='rush-share-chart'), className="my-3"),
                            html.Hr(),
                            dcc.Markdown("""
                            This chart plots the share of opportunities a running back has on their team versus
                            the their share of rushing production.
                            
                            **Rushing Attempt Share** refers to how often a player is is given a rushing attempt on their team.
                            
                            **Rushing Yard Share** refers to how many yards a runningback has rushed with respect to their team.
                            """,
                                         className="text-muted fst-italic mt-3")
                        ])
                    ], className="mt-3")
                ], width=12)
            ])
        ]),
    ])
], fluid=True)


# --- Callbacks to Enable/Disable League-Specific Controls ---
@app.callback(
    [Output('owner-name-dropdown', 'options'),
     Output('owner-name-dropdown', 'disabled'),
     Output('show-taken-draft-checkbox', 'options'),  # Control options to disable
     Output('show-taken-proj-checkbox', 'options'),  # Control options to disable
     Output('league-id-alert', 'children'),
     Output('league-id-alert', 'is_open'),
     Output('league-id-alert', 'color')],
    [Input('load-league-button', 'n_clicks'),
     Input('league-id-input', 'n_submit')],
    [State('league-id-input', 'value')]
)
def update_owner_dropdown(n_clicks, n_submit, league_id):
    """
    Populates the owner ID dropdown based on the entered league ID. If no league_id provided,
    disable the dropdown along with the show_taken checkboxes.

    This callback is triggered whenever the 'league-id-input' value changes.
    It fetches the league's user data and formats it for the dropdown.
    """
    # Prevent callback from firing with an empty league ID.
    if not league_id:
        return [], True, [], [], None, False, ""

    # Log the attempt to load league data
    logger.info(f"Attempting to load league data for ID: {league_id}")

    try:
        league_df = get_league_info(league_id)

        if league_df.is_empty():
            logger.warning(f"No league data found for ID: {league_id}")
            # Invalid League ID
            return ([], True, [], [],
                    "Invalid League ID provided. Please check the ID and try again.", True, "danger")
        else:
            logger.info(f"Successfully loaded league data for ID: {league_id}")
            owner_options = (
                league_df.select(pl.col('owner_name').alias('label'),
                                 pl.col('owner_name').alias('value')).to_dicts())
            checkbox_options = [{'label': 'Show Taken Players', 'value': 'show_taken'}]  # Default control options to enable.
            # Enable the controls on success
            return (owner_options, False, checkbox_options, checkbox_options,
                    "League data loaded successfully!", True, "success")
    except Exception as e:
        logger.error(f"Error loading league data for ID {league_id}: {e}")
        return ([], True, [], [],
                "An error occurred while loading league data.", True, "danger")


# --- Callback to Check for Offseason/Empty Data ---
@app.callback(
    Output('offseason-alert', 'is_open'),
    [Input('draft-positional-board-store', 'data')]
)
def check_offseason_data(pos_data):
    """
    Checks if the draft board data is empty (likely due to offseason/pre-draft status).
    If so, it shows an alert to the user.
    """
    if not pos_data:
        return False  # No data loaded yet

    try:
        # Load the data to check if it's empty or missing columns
        df = pl.read_json(io.StringIO(pos_data))
        
        # If the dataframe is empty (no rows/columns) or missing the key 'Pos' column
        if df.is_empty() or 'Pos' not in df.columns:
            logger.info("Offseason data detected: Positional draft board is empty or missing 'Pos' column.")
            return True
            
        return False

    except Exception as e:
        # If any error occurs reading the data, assume it's invalid/empty
        logger.error(f"Error checking offseason data: {e}")
        return True


# --- Callback to fetch and store league-specific data ---
@app.callback(
    Output('league-info-store', 'data'),
    [Input('load-league-button', 'n_clicks'),
     Input('league-id-input', 'n_submit')],
    [State('league-id-input', 'value')]
)
def update_league_store(n_clicks, n_submit, league_id):
    """
    Fetches league data from the Sleeper API when the league_id changes and stores it as JSON in a dcc.Store.
    """
    if not league_id:
        return None  # Return None if no ID is provided

    logger.info(f"Fetching league info store for ID: {league_id}")
    league_df = get_league_info(league_id)
    return league_df.write_json()


# --- Callback to Update Overview Tab ---
@app.callback(
    [Output('overview-roster-title', 'children'),
     Output('overview-roster-list', 'children'),
     Output('overview-strength-list', 'children'),
     Output('overview-radar-chart', 'figure')],
    [Input('owner-name-dropdown', 'value'),
     Input('draft-overall-board-store', 'data')]
)
def update_overview_tab(owner_name, draft_data):
    """
    Generates the content for the Overview tab:
    1. Left Column: User's roster by position.
    2. Right Upper Column: Team strength rankings vs the league.
    3. Right Lower Column: Radar chart of team strength.
    """
    empty_msg = html.Div("Please select a Sleeper league and owner name.", style={'textAlign': 'center', 'color': 'grey'})

    if not draft_data or not owner_name:
        return "Roster", empty_msg, empty_msg, go.Figure()

    # 1. Load Data and Calculate Values
    board_df = pl.read_json(io.StringIO(draft_data))

    # Check if we have ownership data
    if 'Owner' not in board_df.columns or board_df['Owner'][0] == 'N/A':
        msg = html.Div("Please enter a valid League ID.", style={'textAlign': 'center', 'color': 'grey'})
        return "Roster", msg, msg, go.Figure()

    # Calculate roster and team strengths
    user_roster, user_ranks, league_size = analyze_team(board_df, owner_name)

    # --- Build Left Column: User's Roster ---
    roster_components = []
    for pos in ['QB', 'RB', 'WR', 'TE']:
        pos_players = user_roster.filter(pl.col('Pos') == pos)
        if not pos_players.is_empty():
            roster_components.append(html.H4(pos, style={'borderBottom': '1px solid #555', 'marginBottom': '5px'}))
            
            # Header for the tabular layout
            header = html.Div([
                html.Span("Player", style={'fontWeight': 'bold', 'width': '50%'}),
                html.Span("Team", style={'fontWeight': 'bold', 'width': '15%'}),
                html.Span("Age", style={'fontWeight': 'bold', 'width': '15%'}),
                html.Span("Value", style={'fontWeight': 'bold', 'width': '20%', 'textAlign': 'right'}),
            ], style={'display': 'flex', 'justifyContent': 'space-between', 'padding': '5px 0', 'borderBottom': '1px solid #ccc'})
            
            player_list = [header]
            
            for row in pos_players.iter_rows(named=True):
                player_list.append(html.Div([
                    html.Span(row['Player'], style={'fontWeight': 'bold', 'width': '50%'}),
                    html.Span(row['Team'], style={'width': '15%'}),
                    html.Span(row['Age'], style={'width': '15%'}),
                    html.Span(f"({row['Value']})", style={'color': 'grey', 'fontSize': '0.9em', 'width': '20%', 'textAlign': 'right'}),
                ], style={'display': 'flex', 'justifyContent': 'space-between', 'padding': '5px 0', 'borderBottom': '1px solid #eee'}))

            roster_components.append(html.Div(player_list, style={'marginBottom': '15px'}))

    roster_title = f"{owner_name}'s Roster"

    # --- Build Right Column: Strength Analysis ---
    strength_components = []

    # Helper function for ordinal suffix (1st, 2nd, 3rd)
    def ordinal(n):
        return "%d%s" % (n, "tsnrhtdd"[(n // 10 % 10 != 1) * (n % 10 < 4) * n % 10::4])

    strength_list_items = []
    for pos in ['Overall', 'QB', 'RB', 'WR', 'TE']:
        rank_row = user_ranks.filter(pl.col('Pos') == pos)
        if not rank_row.is_empty():
            rank = int(rank_row['Rank'][0])
            total_val = rank_row['Total Value'][0]
            avg_val = rank_row['Avg Value'][0]
            diff = total_val - avg_val

            # Color code based on rank (Top third Green, Bottom third Red, else Orange)
            rank_color = 'text-warning'
            if rank <= league_size / 3: rank_color = 'text-success'  # Green
            elif rank >= (2 * league_size) / 3:
                rank_color = 'text-danger'  # Red

            diff_color = 'text-success' if diff >= 0 else 'text-danger'
            diff_sign = '+' if diff >= 0 else ''
            
            strength_list_items.append(
                dbc.ListGroupItem([
                    html.Div([
                        html.H5(pos, className="m-0"),
                        html.Span(f"Rank: {ordinal(rank)}", className=f"fw-bold {rank_color}")
                    ], className="d-flex justify-content-between align-items-center mb-1"),
                    html.Div([
                        html.Small(f"Total Value: {total_val}", className="text-muted"),
                        html.Small(f"Diff.: {diff_sign}{int(diff)}", className=f"fw-bold {diff_color}")
                    ], className="d-flex justify-content-between align-items-center")
                ])
            )
            
    strength_components = dbc.ListGroup(strength_list_items)

    # --- Generate Radar Chart ---
    radar_fig = create_team_radar_chart(user_ranks, league_size)

    return roster_title, roster_components, strength_components, radar_fig


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
    logger.info("Updating board stores.")
    league_df = pl.read_json(io.StringIO(league_data)) if league_data else None

    # --- Create and store the full positional draft board ---
    draft_positional_board_df = create_board(league_df=league_df, draft=True, positional=True)
    draft_positional_data = draft_positional_board_df.write_json()

    # --- Create and store the full overall draft board ---
    draft_overall_board_df = create_board(league_df=league_df, draft=True, positional=False)
    draft_overall_data = draft_overall_board_df.write_json()

    # --- Create and store the full weekly board (all positions) ---
    weekly_board_df = create_board(league_df=league_df, draft=False, positional=True)  # positional is ignored
    weekly_data = weekly_board_df.write_json()
    
    logger.info("Board stores updated.")

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

    # Check for empty data before filtering
    if board_df.is_empty() or 'Pos' not in board_df.columns:
        return [], [], "", []

    # Filter for the selected position
    if position != 'Overall':
        board_df = board_df.filter(pl.col('Pos') == position)

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
    columns_to_drop = ['fantasypros_id', 'Best', 'Worst', 'scrape_date']

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
        return [], [], "", []  # Return empty list for styles

    # Load the full board from the store
    board_df = pl.read_json(io.StringIO(weekly_data))

    # Check for empty data before filtering
    if board_df.is_empty() or 'Pos' not in board_df.columns:
        return [], [], "", []

    # Filter for the selected position
    board_df = board_df.filter(pl.col('Pos') == position)

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
    columns_to_drop = ['fantasypros_id', 'Best', 'Worst', 'scrape_date', 'Pos']

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
        Input('owner-name-dropdown', 'value')  # Add owner name as an Input
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

    # Check for empty data before filtering
    if board_df.is_empty() or 'Pos' not in board_df.columns:
        return dash.no_update

    position_df = board_df.filter(pl.col('Pos') == position)

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

    # Check for empty data before filtering
    if board_df.is_empty() or 'Pos' not in board_df.columns:
        return dash.no_update

    position_df = board_df.filter(pl.col('Pos') == position)

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
    values_df = create_trade_values(board_df)

    # --- Generate Conditional Styling ---
    styles = []
    if league_data and owner_name:
        styles.append({
            'if': {'filter_query': '{Owner} = "' + owner_name + '"'},
            'backgroundColor': 'rgba(0, 123, 255, 0.15)',
        })

    # Helper function to prepare data for positional tables
    def prep_value_tables(pos: str):
        pos_values_df = values_df.filter(pl.col('Pos') == pos).sort('Value', descending=True)

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
    Output('rec-share-chart', 'figure'),
    [
        Input('owner-name-dropdown', 'value')
    ],
    [State('league-info-store', 'data')]
)
def update_rec_share_chart(owner_name, league_data):
    """
    Computes full-season receiving share data and generates the scatter plot visualization.
    """
    # Load in receiving share data
    league_df = pl.read_json(io.StringIO(league_data)) if league_data else None
    share_df = receiving_share(league_df=league_df)

    if share_df.is_empty():
        return go.Figure()

    # Generate the Plotly figure, passing the owner_name for highlighting
    return create_rec_share_chart(share_df, user_name=owner_name)


# --- Callback to Update Rushing Share Chart ---
@app.callback(
    Output('rush-share-chart', 'figure'),
    [
        Input('owner-name-dropdown', 'value')
    ],
    [State('league-info-store', 'data')]
)
def update_rush_share_chart(owner_name, league_data):
    """
    Computes full-season receiving share data and generates the scatter plot visualization.
    """
    # Load in receiving share data
    league_df = pl.read_json(io.StringIO(league_data)) if league_data else None
    share_df = rushing_share(league_df=league_df)

    if share_df.is_empty():
        return go.Figure()

    # Generate the Plotly figure, passing the owner_name for highlighting
    return create_rush_share_chart(share_df, user_name=owner_name)


# --- Run debug Application ---
if __name__ == '__main__':
    app.run(debug=True)
