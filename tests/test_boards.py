import pytest
import polars as pl
from polars.testing import assert_frame_equal

# Functions to test
from src.boards import create_board, add_owners, add_ages


# --- Test Data Fixtures ---

@pytest.fixture
def mock_draft_rankings():
    """A mock Polars DataFrame for load_ff_rankings(type='draft') with various ecr_types."""
    return pl.DataFrame({
        'id': [1, 2, 3, 4, 5],
        'player': ['Player One', 'Player Two', 'Player Three', 'Player Four', 'Player Five'],
        'team': ['Team One', 'Team Two', 'Team Three', 'Team One', 'Team Two'],
        'bye': [5, 6, 5, 7, 8],
        'ecr_type': ['dp', 'dp', 'do', 'do', 'dp'],  # dp: positional, do: overall
        'pos': ['RB', 'WR', 'RB', 'QB', 'TE'],
        'ecr': [1.5, 2.5, 3.5, 4.5, 5.5],
        'best': [1, 2, 3, 4, 5],
        'worst': [2, 3, 4, 5, 6],
        'sd': [0.5, 0.5, 0.5, 0.5, 0.5],
        'scrape_date': ['2023-01-01', '2023-01-01', '2023-01-01', '2023-01-01', '2023-01-01']
    })


@pytest.fixture
def mock_weekly_rankings():
    """A mock Polars DataFrame for load_ff_rankings(type='week')."""
    return pl.DataFrame({
        'fantasypros_id': [1, 2, 3, 4, 5],
        'player_name': ['Player One', 'Player Two', 'Player Three', 'Player Four', 'Player Five'],
        'team': ['Team One', 'Team Two', 'Team Three', 'Team One', 'Team Two'],
        'pos': ['RB', 'WR', 'RB', 'QB', 'TE'],
        'pos_rank': ['RB1', 'WR1', 'RB2', 'QB1', 'TE1'],
        'player_opponent': ['Opponent One', 'Opponent Two', 'Opponent One', 'Opponent Three', 'Opponent Two'],
        'start_sit_grade': ['A', 'A', 'B', 'A', 'C'],
        'ecr': [1.5, 2.5, 3.5, 4.5, 5.5],
        'best': [1, 2, 3, 4, 5],
        'worst': [2, 3, 4, 5, 6],
        'sd': [0.5, 0.5, 0.5, 0.5, 0.5],
        'r2p_pts': [20.5, 15.5, 13.4, 25.3, 18.2],
        'scrape_date': ['2023-01-01', '2023-01-01', '2023-01-01', '2023-01-01', '2023-01-01']
    })


@pytest.fixture
def mock_player_ids_with_age():
    """A mock Polars DataFrame for load_ff_playerids() with age."""
    return pl.DataFrame(
        {'fantasypros_id': [1, 2, 3, 4, 5], 'age': [24, 28, 22, 30, 25]},
        schema={'fantasypros_id': pl.Int64, 'age': pl.Int64}
    )


@pytest.fixture
def mock_league_info_for_owners():
    """A mock Polars DataFrame from get_league_info for testing add_owners."""
    return pl.DataFrame({
        "owner_name": ["User One", "User Two"],
        "fantasypros_ids": [
            [1, 4, 5],  
            [2, 3]       
        ]
    })


# --- Unit Tests for add_ages ---

def test_add_ages(mocker, mock_player_ids_with_age):
    """Tests that add_ages correctly joins and adds the 'Age' column."""
    # Arrange
    mocker.patch('src.boards.load_ff_playerids', return_value=mock_player_ids_with_age)
    input_df = pl.DataFrame(
        {'fantasypros_id': [1, 2, 99]}, # Player 99 has no age in the mock data
        schema={'fantasypros_id': pl.Int64}
    )

    # Act
    result_df = add_ages(input_df)

    # Assert
    expected_df = pl.DataFrame(
        {'fantasypros_id': [1, 2, 99], 'Age': [24, 28, None]},
        schema={'fantasypros_id': pl.Int64, 'Age': pl.Int64}
    )
    assert_frame_equal(result_df, expected_df)


# --- Unit Tests for add_owners ---

def test_add_owners(mocker, mock_league_info_for_owners):
    """Tests that add_owners correctly joins owner names and fills nulls for free agents."""
    # Arrange
    mocker.patch('src.boards.get_league_info', return_value=mock_league_info_for_owners)
    input_df = pl.DataFrame(
        {'fantasypros_id': [1, 2, 99]}, # Player 99 is a free agent
        schema={'fantasypros_id': pl.Int64}
    )

    # Act
    result_df = add_owners('dummy_league_id', input_df)

    # Assert
    expected_df = pl.DataFrame(
        {'fantasypros_id': [1, 2, 99], 'Owner': ['User One', 'User Two', 'Free Agent']},
        schema={'fantasypros_id': pl.Int64, 'Owner': pl.String}
    )
    assert_frame_equal(result_df, expected_df)


# --- Unit Tests for create_board ---

def test_create_board_draft_positional_with_league(mocker, mock_draft_rankings, mock_player_ids_with_age, mock_league_info_for_owners):
    """Tests create_board for a positional draft board with a league_id provided."""
    # Arrange
    mocker.patch('src.boards.load_ff_rankings', return_value=mock_draft_rankings)
    mocker.patch('src.boards.load_ff_playerids', return_value=mock_player_ids_with_age)
    mocker.patch('src.boards.get_league_info', return_value=mock_league_info_for_owners)

    # Act
    result_df = create_board(league_id='dummy_id', draft=True, positional=True)

    # Assert
    # It should filter for 'dp' players (1, 2, 5), add their ages and owners.
    assert result_df.shape[0] == 3
    assert 'Age' in result_df.columns
    assert 'Owner' in result_df.columns
    assert result_df.filter(pl.col('Player') == 'Player One')['Owner'].item() == 'User One'
    assert result_df.filter(pl.col('Player') == 'Player Two')['Owner'].item() == 'User Two'
    assert result_df.filter(pl.col('Player') == 'Player Five')['Owner'].item() == 'User One'
    assert result_df.filter(pl.col('Player') == 'Player One')['Age'].item() == 24


def test_create_board_draft_overall_no_league(mocker, mock_draft_rankings, mock_player_ids_with_age):
    """Tests create_board for an overall draft board without a league_id."""
    # Arrange
    mocker.patch('src.boards.load_ff_rankings', return_value=mock_draft_rankings)
    mocker.patch('src.boards.load_ff_playerids', return_value=mock_player_ids_with_age)

    # Act
    result_df = create_board(league_id=None, draft=True, positional=False)

    # Assert
    # It should filter for 'do' players (3, 4) and add a placeholder 'N/A' for Owner.
    assert result_df.shape[0] == 2
    assert 'Age' in result_df.columns
    assert 'Owner' in result_df.columns
    assert result_df['Owner'].unique().to_list() == ['N/A']
    assert ~result_df.filter(pl.col('Player') == 'Player Three').is_empty()
    assert ~result_df.filter(pl.col('Player') == 'Player Four').is_empty()
    assert result_df.filter(pl.col('Player') == 'Player Three')['Age'].item() == 22


def test_create_board_weekly(mocker, mock_weekly_rankings, mock_league_info_for_owners):
    """Tests create_board for a weekly board with a league_id provided."""
    # Arrange
    mocker.patch('src.boards.load_ff_rankings', return_value=mock_weekly_rankings)
    mocker.patch('src.boards.get_league_info', return_value=mock_league_info_for_owners)

    # Act
    result_df = create_board(league_id='dummy_id', draft=False, positional=True) # positional is ignored for weekly

    # Assert
    # It should not add ages, but it should add owners.
    assert result_df.shape[0] == 5
    assert 'Age' not in result_df.columns
    assert 'Proj. Points' in result_df.columns
    assert 'Owner' in result_df.columns
    assert result_df.filter(pl.col('Player') == 'Player One')['Owner'].item() == 'User One'
    assert result_df.filter(pl.col('Player') == 'Player Two')['Owner'].item() == 'User Two'
    assert result_df.filter(pl.col('Player') == 'Player Three')['Owner'].item() == 'User Two'


def test_create_board_handles_empty_data(mocker):
    """Tests that create_board returns an empty DataFrame if the initial load fails."""
    # Arrange
    mocker.patch('src.boards.load_ff_rankings', return_value=pl.DataFrame())

    # Act
    result_df_draft = create_board(league_id=None, draft=True, positional=True)
    result_df_weekly = create_board(league_id=None, draft=False, positional=True)

    # Assert
    assert result_df_draft.is_empty()
    assert result_df_weekly.is_empty()
