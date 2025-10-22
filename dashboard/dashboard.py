"""
This script defines the layout and callback logic for the Sleeper Dynasty Assistant dashboard.
"""

import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output

from src.boards import create_board, remove_taken
from src.league_info import get_league_info

from pathlib import Path
from nflreadpy.config import update_config

# --- Configure Cache ---
cache_dir = Path(__file__).resolve().parent.parent / 'cache'
update_config(cache_mode="filesystem", cache_dir=cache_dir, verbose=True)

# Initialize the Dash application. The __name__ is for Dash to locate static assets.
app = dash.Dash(__name__)

# --- App Layout ---
# The layout is the root component that describes the application's appearance.
app.layout = html.Div([
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
        
        # Owner ID Dropdown Group
        html.Div([
            html.Label("Select Owner: ", style={'margin-right': '10px'}),
            dcc.Dropdown(
                id='owner-id-dropdown',
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

            dash_table.DataTable(
                id='draft-table',
                style_header={'backgroundColor': 'rgb(30, 30, 30)', 'color': 'white'},
                style_cell={'backgroundColor': 'rgb(50, 50, 50)', 'color': 'white'},
            )
        ]),

        # --- Weekly Projections Tab ---
        dcc.Tab(label='Projections', children=[
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

            dash_table.DataTable(
                id='proj-table',
                style_header={'backgroundColor': 'rgb(30, 30, 30)', 'color': 'white'},
                style_cell={'backgroundColor': 'rgb(50, 50, 50)', 'color': 'white'},
            )

        ]),

        # --- Trade Calculator Tab (Placeholder) ---
        #

        #]),
    ]),
])


# --- Callback to Populate Owner Dropdown ---
@app.callback(
    Output('owner-id-dropdown', 'options'),
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
        league_df.select(['owner_name', 'owner_id'])
        .rename({'owner_name': 'label', 'owner_id': 'value'})
        .to_dicts()
    )
    
    return owner_options


# --- Callback to Update Draft Table ---
@app.callback(
    [
        Output('draft-table', 'data'),
        Output('draft-table', 'columns')
    ],
    [
        Input('league-id-input', 'value'),
        Input('owner-id-dropdown', 'value'),
        Input('position-draft-selection', 'value'),
        Input('show-taken-draft-checkbox', 'value')
    ]
)

def update_draft_table(league_id, owner_id, position, show_taken_value):
    """
    Updates the dynasty draft board table based on user selections.

    This callback listens for changes in the global filters or the tab-specific
    filters and regenerates the draft board data accordingly.
    """
    # Ensure all necessary inputs are provided before attempting to fetch data.
    if not all([league_id, owner_id, position]):
        return [], []

    # The checklist's value is a list. It's not empty if the box is checked.
    show_taken_flag = bool(show_taken_value)

    # Call the data-layer function to get the dynasty draft board DataFrame.
    board_df = create_board(position, draft=True)
    
    # If the 'Show Taken Players' box is NOT checked, remove them.
    if not show_taken_flag:
        board_df = remove_taken(league_id, owner_id, board_df)

    # Format the DataFrame for the Dash DataTable
    columns = [{"name": i, "id": i} for i in board_df.columns]
    data = board_df.to_dicts()

    return data, columns

# --- Callback to Update Projections Table ---
@app.callback(
    [
        Output('proj-table', 'data'),
        Output('proj-table', 'columns')
    ],
    [
        Input('league-id-input', 'value'),
        Input('owner-id-dropdown', 'value'),
        Input('position-proj-selection', 'value'),
        Input('show-taken-proj-checkbox', 'value')
    ]
)

def update_proj_table(league_id, owner_id, position, show_taken_value):
    """
    Updates the weekly projections table based on user selections.

    This callback listens for changes in the global filters or the tab-specific
    filters and regenerates the weekly projection data accordingly.
    """
    # Ensure all necessary inputs are provided before attempting to fetch data.
    if not all([league_id, owner_id, position]):
        return [], []

    # The checklist's value is a list. It's not empty if the box is checked.
    show_taken_flag = bool(show_taken_value)

    # Call the data-layer function to get the weekly projection board DataFrame.
    board_df = create_board(position, draft=False)

    # If the 'Show Taken Players' box is NOT checked, remove them.
    if not show_taken_flag:
        board_df = remove_taken(league_id, owner_id, board_df)

    # Format the DataFrame for the Dash DataTable
    columns = [{"name": i, "id": i} for i in board_df.columns]
    data = board_df.to_dicts()

    return data, columns


# --- Run the Application ---
# This block allows the script to be run directly to start the development server.
# `debug=True` enables features like hot-reloading and the in-browser error console.
if __name__ == '__main__':
    app.run(debug=True)
