import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output

from data.dynasty_board import create_draft_board
from data.league_info import get_league_info

# Initialize the Dash application
app = dash.Dash(__name__)

# --- App Layout ---
app.layout = html.Div([
    html.H1("Sleeper Dynasty Assistant"),

    # Parent container for the top-row inputs
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

    # Tabs for different views
    dcc.Tabs([
        # Draft Board Tab
        dcc.Tab(label='Draft Board', children=[
            html.Br(),
            html.Div([
                # Group for left-aligned items
                html.Div([
                    html.Label("Position: ", style={'margin-right': '20px'}),
                    dcc.RadioItems(
                        id='position-selection',
                        options=[
                            {'label': 'Quarterback', 'value': 'qb'},
                            {'label': 'Running Back', 'value': 'rb'},
                            {'label': 'Wide Receiver', 'value': 'wr'},
                            {'label': 'Tight End', 'value': 'te'},
                        ],
                        value='qb',  # Default value
                        inline=True,  # Display options horizontally
                        labelStyle={'margin-right': '20px'}  # Add space between radio items
                    ),
                ], style={'display': 'flex', 'align-items': 'center'}),

                # This item will be pushed to the right
                dcc.Checklist(
                    id='show-taken-checkbox',
                    options=[{'label': 'Show Taken Players', 'value': 'show_taken'}],
                    value=[],  # Default to unchecked
                ),
            ], style={'display': 'flex', 'align-items': 'center', 'justify-content': 'space-between'}),

            html.Br(),

            dash_table.DataTable(
                id='player-table',
                style_header={'backgroundColor': 'rgb(30, 30, 30)', 'color': 'white'},
                style_cell={'backgroundColor': 'rgb(50, 50, 50)', 'color': 'white'},
            )
        ]),

        # Weekly Projections Tab
        dcc.Tab(label='Projections', children=[

        ]),

        # Trade Calculator Tab
        dcc.Tab(label='Trade Calculator', children=[

        ]),
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
    """

    # Do nothing if league_id is blank
    if not league_id:
        return []

    league_df = get_league_info(league_id)
    # Create a list of dictionaries for the dropdown options
    owner_options = [
        {'label': row['owner_name'], 'value': row['owner_id']}
        for index, row in league_df.iterrows()
    ]
    return owner_options


# --- Callback to Update Player Table ---
@app.callback(
    [
        Output('player-table', 'data'),
        Output('player-table', 'columns')
    ],
    [
        Input('league-id-input', 'value'),
        Input('owner-id-dropdown', 'value'),
        Input('position-selection', 'value'),
        Input('show-taken-checkbox', 'value')
    ]
)

def update_player_table(league_id, owner_id, position, show_taken_value):
    """
    Updates the player table based on league, owner, and position selections.
    It filters out players who are already on other owners' rosters.
    """
    if not all([league_id, owner_id, position]):
        return [], []

    # The checklist's value is a list. It's not empty if the box is checked.
    show_taken_flag = bool(show_taken_value)

    # Fetch the projection data
    board_df = create_draft_board(position, league_id, owner_id, show_taken=show_taken_flag)

    # Format the DataFrame for the Dash DataTable
    columns = [{"name": i, "id": i} for i in board_df.columns]
    data = board_df.to_dict('records')

    return data, columns


# --- Run the Application ---
if __name__ == '__main__':
    app.run(debug=True)
