import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output

from data.dynasty_board import create_draft_board
from data.league_info import get_league_info

# Initialize the Dash application
app = dash.Dash(__name__)

# --- App Layout ---
app.layout = html.Div([
    html.H1("Dynasty Assistant Dashboard"),

    html.Div([
        html.Label("Enter Sleeper League ID:"),
        dcc.Input(
            id='league-id-input',
            type='text',
            placeholder='e.g., 992016434344030208'
        ),
    ]),

    html.Br(),

    html.Div([
        html.Label("Select Owner ID:"),
        dcc.Dropdown(
            id='owner-id-dropdown',
            placeholder='Select your ID'
        ),
    ]),

    html.Br(),

    html.Div([
        html.Label("Select Position:"),
        dcc.Dropdown(
            id='position-dropdown',
            options=[
                {'label': 'Quarterback', 'value': 'qb'},
                {'label': 'Running Back', 'value': 'rb'},
                {'label': 'Wide Receiver', 'value': 'wr'},
                {'label': 'Tight End', 'value': 'te'},
            ],
            placeholder='Select a position'
        ),
    ]),

    html.Br(),

    dash_table.DataTable(
        id='player-table',
        style_header={
            'backgroundColor': 'rgb(30, 30, 30)',
            'color': 'white'
        },
        style_cell={
            'backgroundColor': 'rgb(50, 50, 50)',
            'color': 'white'
        },
    )
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
        Input('position-dropdown', 'value')
    ]
)

def update_player_table(league_id, owner_id, position):
    """
    Updates the player table based on league, owner, and position selections.
    It filters out players who are already on other owners' rosters.
    """
    if not all([league_id, owner_id, position]):
        return [], []

    # Fetch the projection data
    board_df = create_draft_board(position, league_id, owner_id)

    # Format the DataFrame for the Dash DataTable
    columns = [{"name": i, "id": i} for i in board_df.columns]
    data = board_df.to_dict('records')

    return data, columns


# --- Run the Application ---
if __name__ == '__main__':
    app.run(debug=True)
