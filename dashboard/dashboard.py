"""
This script defines the layout and callback logic for the Sleeper Dynasty Assistant dashboard.
"""
import polars as pl
import io

# --- Dash/Plotly Imports ---
import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output, State
import plotly.graph_objects as go

# --- Import Helper Functions ---
from src.boards import create_board
from src.league_info import get_league_info
from src.tiers import create_tiers
from src.visualizations import create_tier_chart

# --- Configure Cache ---
from pathlib import Path
from nflreadpy.config import update_config

cache_dir = Path(__file__).resolve().parent.parent / 'cache'
update_config(cache_mode="filesystem", cache_dir=cache_dir, verbose=True, cache_duration=300)

# Initialize the Dash application. The __name__ is for Dash to locate static assets.
app = dash.Dash(__name__)

# --- App Layout ---
# The layout is the root component that describes the application's appearance.
app.layout = html.Div([
    # --- Data Stores ---
    # These hidden components store the results of expensive computations (the full boards).
    dcc.Store(id='draft-board-store'),
    dcc.Store(id='weekly-board-store'),

    html.H1("Sleeper Dynasty Assistant"),

    # --- Global Controls ---
    # These inputs for league and owner are placed outside the tabs so they
    # can be used as persistent filters across all views.
    html.Div([
        # League ID Input Group
        html.Div([
            html.Label("Enter Sleeper League ID: ", style={'margin-right': '10px'}),
            dcc.Input(
                id='league-id-input',
                type='text',
                placeholder='e.g., 992016434344030208'
            ),
        ], style={'display': 'flex', 'align-items': 'center', 'margin-right': '50px'}),

        # Owner Name Dropdown Group
        html.Div([
            html.Label("Select Owner: ", style={'margin-right': '10px'}),
            dcc.Dropdown(
                id='owner-name-dropdown',
                placeholder='Your username',
                style={'width': '250px'}
            ),
        ], style={'display': 'flex', 'align-items': 'center'}),
    ], style={'display': 'flex', 'align-items': 'center'}),

    html.Br(),

    # --- Main Tabbed Interface ---
    dcc.Tabs([
        # --- Dynasty Draft Board Tab ---
        dcc.Tab(label='Draft Board', children=[
            html.Br(),
            html.Div([
                # Group for left-aligned items
                html.Div([
                    html.Label("Position: ", style={'margin-right': '20px'}),
                    dcc.RadioItems(
                        id='position-draft-selection',
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
                ], style={'display': 'flex', 'align-items': 'center'}),

                # This item will be pushed to the right
                dcc.Checklist(
                    id='show-taken-draft-checkbox',
                    options=[{'label': 'Show Taken Players', 'value': 'show_taken'}],
                    value=[],  # Default to unchecked
                ),
            ], style={'display': 'flex', 'align-items': 'center', 'justify-content': 'space-between'}),

            html.Br(),

            # Add a placeholder for the "Last Update" text
            html.Div(id='draft-last-update', style={'text-align': 'right', 'color': 'grey',
                                                    'font-style': 'italic', 'margin-bottom': '5px'}),

            dash_table.DataTable(
                id='draft-table',
                #style_header={'backgroundColor': 'rgb(30, 30, 30)', 'color': 'white'},
                #style_cell={'backgroundColor': 'rgb(50, 50, 50)', 'color': 'white'},
            )
        ]),

        # --- Weekly Projections Tab ---
        dcc.Tab(label='Weekly Projections', children=[
            html.Br(),
            html.Div([
                # Group for left-aligned items
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
                ], style={'display': 'flex', 'align-items': 'center'}),

                # This item will be pushed to the right
                dcc.Checklist(
                    id='show-taken-proj-checkbox',
                    options=[{'label': 'Show Taken Players', 'value': 'show_taken'}],
                    value=[],  # Default to unchecked
                ),
            ], style={'display': 'flex', 'align-items': 'center', 'justify-content': 'space-between'}),

            html.Br(),

            # Add a placeholder for the "Last Update" text
            html.Div(id='proj-last-update', style={'text-align': 'right', 'color': 'grey',
                                                   'font-style': 'italic', 'margin-bottom': '5px'}),

            dash_table.DataTable(
                id='proj-table',
                #style_header={'backgroundColor': 'rgb(30, 30, 30)', 'color': 'white'},
                #style_cell={'backgroundColor': 'rgb(50, 50, 50)', 'color': 'white'},
            )

        ]),

        # --- Tiers Visualization Tab ---
        dcc.Tab(label='Positional Rank Tiers', children=[
            html.Br(),
            html.Div([
                # Group for left-aligned items
                html.Div([
                    html.Label("Position: ", style={'margin-right': '20px'}),
                    dcc.RadioItems(
                        id='position-tier-selection',
                        options=[
                            {'label': 'Quarterback', 'value': 'QB'},
                            {'label': 'Running Back', 'value': 'RB'},
                            {'label': 'Wide Receiver', 'value': 'WR'},
                            {'label': 'Tight End', 'value': 'TE'},
                        ],
                        value='RB',  # Default value
                        inline=True,
                        labelStyle={'margin-right': '20px'}
                    ),
                ], style={'display': 'flex', 'align-items': 'center'}),

                # Radio buttons to select board type on the right
                dcc.RadioItems(
                    id='board-type-selection',
                    options=[
                        {'label': 'Draft Tiers', 'value': 'draft'},
                        {'label': 'Weekly Tiers', 'value': 'weekly'},
                    ],
                    value='weekly', # Default to weekly tiers
                    inline=True,
                    labelStyle={'margin-left': '20px'}
                ),

            ], style={'display': 'flex', 'align-items': 'center', 'justify-content': 'space-between'}),

            html.Br(),

            # Graph component to display the Plotly figure
            dcc.Graph(id='tier-chart-graph')
        ]),
    ]),
])


# --- Callback to Populate Owner Dropdown ---
@app.callback(
    Output('owner-name-dropdown', 'options'),
    [Input('league-id-input', 'value')]
)

def update_owner_dropdown(league_id):
    """
    Populates the owner ID dropdown based on the entered league ID.

    This callback is triggered whenever the 'league-id-input' value changes.
    It fetches the league's user data and formats it for the dropdown.
    """
    # Prevent callback from firing with an empty league ID.
    if not league_id:
        return []

    league_df = get_league_info(league_id)
    # Format the owner data into a list of dictionaries as required by dcc.Dropdown
    owner_options = (
        league_df.select(pl.col('owner_name').alias('label'),
                         pl.col('owner_name').alias('value')).to_dicts())

    return owner_options


# --- Master Callback to Compute and Store Full Board Data ---
@app.callback(
    [Output('draft-board-store', 'data'),
     Output('weekly-board-store', 'data')],
    [Input('league-id-input', 'value')]
)
def update_board_stores(league_id):
    """
    This master callback runs the expensive computations once and stores the results.
    It's triggered only when the league ID changes, signifying a new context.
    """
    if not league_id:
        return None, None

    # --- Create and store the full draft board (all positions) ---
    # This is the expensive part that we only want to do once per session.
    draft_board_df = create_board(league_id=league_id, draft=True)
    # Convert the DataFrame to a JSON string for storage.
    draft_data = draft_board_df.write_json()

    # --- Create and store the full weekly board (all positions) ---
    weekly_board_df = create_board(league_id=league_id, draft=False)
    weekly_data = weekly_board_df.write_json()

    return draft_data, weekly_data


# --- Callback to Update Draft Table ---
@app.callback(
    [
        Output('draft-table', 'data'),
        Output('draft-table', 'columns'),
        Output('draft-last-update', 'children')
    ],
    [
        Input('owner-name-dropdown', 'value'),
        Input('draft-board-store', 'data'),  # Listen to the data store
        Input('position-draft-selection', 'value'),
        Input('show-taken-draft-checkbox', 'value')
    ],
    [State('league-id-input', 'value')]  # Get league_id without re-triggering
)
def update_draft_table(owner_name, draft_data, position, show_taken_value, league_id):
    """
    Updates the dynasty draft board table based on user selections.

    This is a "consumer" callback. It reads pre-computed data from the dcc.Store
    and performs fast, in-memory filtering.
    """
    # Ensure all necessary inputs are provided before attempting to fetch data.
    if not all([owner_name, draft_data, position, league_id]):
        return [], [], ""

    # Load the full board from the store
    board_df = pl.read_json(io.StringIO(draft_data))

    # Filter for the selected position
    board_df = board_df.filter(pl.col('pos') == position)

    # The checklist's value is a list. It's not empty if the box is checked.
    show_taken_flag = bool(show_taken_value)

    # Apply roster filtering if requested
    if not show_taken_flag:
        board_df = board_df.filter((pl.col('Owner') == owner_name) | (pl.col('Owner') == 'Free Agent'))

    # Get scrape_date to represent the last update of the data.
    last_update_text = ""
    if not board_df.is_empty() and 'scrape_date' in board_df.columns:
        # Get the date from the first row and format it
        scrape_date = board_df['scrape_date'][0]
        last_update_text = f"Last Update: {scrape_date}"

    # Drop the fantasypros_id and scrape_date columns for readability
    board_df = board_df.drop(['fantasypros_id', 'scrape_date', 'pos'])

    # Format the DataFrame for the Dash DataTable
    columns = [{"name": i, "id": i} for i in board_df.columns]
    data = board_df.to_dicts()

    return data, columns, last_update_text

# --- Callback to Update Projections Table ---
@app.callback(
    [
        Output('proj-table', 'data'),
        Output('proj-table', 'columns'),
        Output('proj-last-update', 'children')
    ],
    [
        Input('owner-name-dropdown', 'value'),
        Input('weekly-board-store', 'data'),  # Listen to the data store
        Input('position-proj-selection', 'value'),
        Input('show-taken-proj-checkbox', 'value')
    ],
    [State('league-id-input', 'value')]  # Get league_id without re-triggering
)
def update_proj_table(owner_name, weekly_data, position, show_taken_value, league_id):
    """
    Updates the weekly projections table based on user selections.

    This is a "consumer" callback. It reads pre-computed data from the dcc.Store
    and performs fast, in-memory filtering.
    """
    # Ensure all necessary inputs are provided before attempting to fetch data.
    if not all([owner_name, weekly_data, position, league_id]):
        return [], [], ""

    # Load the full board from the store
    board_df = pl.read_json(io.StringIO(weekly_data))

    # Filter for the selected position
    board_df = board_df.filter(pl.col('pos') == position)

    # The checklist's value is a list. It's not empty if the box is checked.
    show_taken_flag = bool(show_taken_value)

    # Apply roster filtering if requested
    if not show_taken_flag:
        board_df = board_df.filter((pl.col('Owner') == owner_name) | (pl.col('Owner') == 'Free Agent'))

    # Get scrape_date to represent the last update of the data.
    last_update_text = ""
    if not board_df.is_empty() and 'scrape_date' in board_df.columns:
        # Get the date from the first row and format it
        scrape_date = board_df['scrape_date'][0]
        last_update_text = f"Last Update: {scrape_date}"

    # Drop the fantasypros_id and scrape_date columns for readability
    board_df = board_df.drop(['fantasypros_id', 'scrape_date', 'pos'])

    # Format the DataFrame for the Dash DataTable
    columns = [{"name": i, "id": i} for i in board_df.columns]
    data = board_df.to_dicts()

    return data, columns, last_update_text


# --- Callback to Update Tiers Chart ---
@app.callback(
    Output('tier-chart-graph', 'figure'),
    [
        Input('draft-board-store', 'data'),   # Listen to draft data
        Input('weekly-board-store', 'data'),  # Listen to weekly data
        Input('position-tier-selection', 'value'),
        Input('board-type-selection', 'value') # New input for board type
    ]
)
def update_tier_chart(draft_data, weekly_data, position, board_type):
    """
    Generates and displays the player tier visualization.

    This callback reads the pre-computed draft board data, filters it,
    calculates tiers, and then creates the chart.
    """
    # Select the correct data source based on the radio button selection
    if board_type == 'draft':
        board_data = draft_data
        n_players = {'QB': 32, 'RB': 64, 'WR': 96, 'TE': 32}
        tier_range = {'QB': range(8, 12 + 1), 'RB': range(10, 14 + 1),
                      'WR': range(12, 16 + 1), 'TE': range(8, 12 + 1)}
    elif board_type == 'weekly':
        board_data = weekly_data
        n_players = {'QB': 24, 'RB': 40, 'WR': 60, 'TE': 24}
        tier_range = {'QB': range(6, 10 + 1), 'RB': range(8, 12 + 1),
                      'WR': range(8, 12 + 1), 'TE': range(6, 10 + 1)}
    else:
        return go.Figure()

    if not board_data or not position:
        return go.Figure()

    # Load and filter the main board data
    board_df = pl.read_json(io.StringIO(board_data))
    position_df = board_df.filter(pl.col('pos') == position)

    # Apply the tiering algorithm
    tiered_df = create_tiers(
        position_df,
        tier_range=tier_range[position],
        n_players=n_players[position]
    )

    # Generate the Plotly figure
    fig = create_tier_chart(tiered_df)

    return fig


# --- Run the Application ---
# This block allows the script to be run directly to start the development server.
# `debug=True` enables features like hot-reloading and the in-browser error console.
if __name__ == '__main__':
    app.run(debug=True)
