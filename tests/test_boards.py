import pytest
import polars as pl
from polars.testing import assert_frame_equal

# Functions to test
from src.boards import create_board, remove_taken, add_ages


# --- Test Data Fixtures ---

@pytest.fixture
def mock_draft_rankings():
    """A mock Polars DataFrame for load_ff_rankings(type='draft')."""
    return pl.DataFrame({
        'id': ['p1', 'p2', 'p3'],
        'player': ['Player One', 'Player Two', 'Player Three'],
        'team': ['TM1', 'TM2', 'TM1'],
        'bye': [5, 6, 5],
        'ecr_type': ['dp', 'dp', 'op'],  # dynasty positional, overall positional
        'pos': ['RB', 'RB', 'RB'],
        'ecr': [1.5, 2.5, 3.5],
        'best': [1, 2, 3],
        'worst': [2, 3, 4],
        'sd': [0.5, 0.5, 0.5],
        'scrape_date': ['2023-01-01', '2023-01-01', '2023-01-01']
    })


@pytest.fixture
def mock_weekly_rankings():
    """A mock Polars DataFrame for load_ff_rankings(type='week')."""
    return pl.DataFrame({
        'fantasypros_id': ['p1', 'p4'],
        'player_name': ['Player One', 'Player Four'],
        'team': ['TM1', 'TM4'],
        'pos': ['RB', 'WR'],
        'pos_rank': [1, 1],
        'player_opponent': ['OPP', 'OPP'],
        'start_sit_grade': ['A', 'B'],
        'ecr': [1.5, 2.5],
        'best': [1, 2],
        'worst': [2, 3],
        'sd': [0.5, 0.5],
        'r2p_pts': [20.5, 15.5],
        'scrape_date': ['2023-01-01', '2023-01-01']
    })


@pytest.fixture
def mock_player_ids_with_age():
    """A mock Polars DataFrame for load_ff_playerids() with age."""
    return pl.DataFrame({
        'fantasypros_id': ['p1', 'p2'],
        'age': [24, 28]
    })


@pytest.fixture
def mock_league_info_for_removal():
    """A mock Polars DataFrame from get_league_info for testing remove_taken."""
    return pl.DataFrame({
        "owner_id": ["123", "456"],
        "fantasypros_ids": [
            ['p1', 'p99'],  # Player p1 is taken by another owner
            ['p2']          # Player p2 is on the user's own roster
        ]
    })


# --- Unit Tests for add_ages ---

def test_add_ages(mocker, mock_player_ids_with_age):
    """Tests that add_ages correctly joins and adds the 'Age' column."""
    # Arrange
    mocker.patch('src.boards.load_ff_playerids', return_value=mock_player_ids_with_age)
    input_df = pl.DataFrame({
        'fantasypros_id': ['p1', 'p2', 'p3'],
        'Player': ['Player One', 'Player Two', 'Player Three'],
        'Team': ['TM1', 'TM2', 'TM1'],
        'Bye': [5, 6, 5],
        'ECR': [1.5, 2.5, 3.5],
        'Best': [1, 2, 3],
        'Worst': [2, 3, 4],
        'Std': [0.5, 0.5, 0.5],
        'scrape_date': ['2023-01-01', '2023-01-01', '2023-01-01']
    })

    # Act
    result_df = add_ages(input_df)

    # Assert
    assert 'Age' in result_df.columns
    assert result_df.filter(pl.col('fantasypros_id') == 'p1')['Age'][0] == 24
    assert result_df.filter(pl.col('fantasypros_id') == 'p2')['Age'][0] == 28
    assert result_df.filter(pl.col('fantasypros_id') == 'p3')['Age'][0] is None  # No age data


# --- Unit Tests for remove_taken ---

def test_remove_taken(mocker, mock_league_info_for_removal):
    """Tests that remove_taken correctly filters out players on other rosters."""
    # Arrange
    mocker.patch('src.boards.get_league_info', return_value=mock_league_info_for_removal)
    input_df = pl.DataFrame({
        'fantasypros_id': ['p1', 'p2', 'p3'],
        'Player': ['Taken Player', 'My Player', 'Available Player']
    })
    user_owner_id = '456'

    # Act
    result_df = remove_taken('dummy_league_id', user_owner_id, input_df)

    # Assert
    assert 'p1' not in result_df['fantasypros_id'].to_list()  # p1 should be removed
    assert 'p2' in result_df['fantasypros_id'].to_list()      # p2 is on my team, should be kept
    assert 'p3' in result_df['fantasypros_id'].to_list()      # p3 is available, should be kept
    assert result_df.shape[0] == 2


# --- Unit Tests for create_board ---

def test_create_board_draft(mocker, mock_draft_rankings, mock_player_ids_with_age):
    """Tests create_board for a dynasty/draft board."""
    # Arrange
    mocker.patch('src.boards.load_ff_rankings', return_value=mock_draft_rankings)
    mocker.patch('src.boards.load_ff_playerids', return_value=mock_player_ids_with_age)

    # Act
    result_df = create_board(pos='RB', draft=True)

    # Assert
    assert result_df.shape[0] == 2  # Only 2 RBs with 'dp' ecr_type
    assert 'Age' in result_df.columns
    assert result_df['fantasypros_id'].dtype == pl.String


def test_create_board_weekly(mocker, mock_weekly_rankings):
    """Tests create_board for a weekly projections board."""
    # Arrange
    mocker.patch('src.boards.load_ff_rankings', return_value=mock_weekly_rankings)

    # Act
    result_df = create_board(pos='RB', draft=False)

    # Assert
    assert result_df.shape[0] == 1  # Only one RB in the mock data
    assert 'Proj. Points' in result_df.columns
    assert result_df['fantasypros_id'].dtype == pl.String


def test_create_board_weekly_no_data(mocker):
    """Tests that create_board returns an empty DataFrame if no data is loaded."""
    # Arrange
    mocker.patch('src.boards.load_ff_rankings', return_value=pl.DataFrame())

    # Act
    result_df = create_board(pos='QB', draft=False)

    # Assert
    assert result_df.is_empty()