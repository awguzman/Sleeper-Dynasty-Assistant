import pytest
import polars as pl
import requests.exceptions
from polars.testing import assert_frame_equal

# Functions to test.
from src.league import get_league_info, translate_owner_id, get_scoring_weights


# --- Test Data Fixtures ---

@pytest.fixture
def mock_sleeper_rosters_response():
    """A mock successful response for the Sleeper rosters API endpoint."""

    class MockResponse:
        status_code = 200

        def json(self):
            return [
                {
                    "owner_id": "123",
                    "players": ["1049", "4034"],
                    "reserve": ["223", "7523"]
                },
                {
                    "owner_id": "456",
                    "players": ["515"],
                    "reserve": None  # Edge case: no reserve players
                }
            ]

    return MockResponse()


@pytest.fixture
def mock_sleeper_users_response():
    """A mock successful response for the Sleeper users API endpoint."""

    class MockResponse:
        status_code = 200

        def json(self):
            return [
                {"user_id": "123", "display_name": "UserOne"},
                {"user_id": "456", "display_name": "UserTwo"}
            ]

    return MockResponse()


@pytest.fixture
def mock_sleeper_league_response():
    """A mock successful response for the Sleeper league settings API endpoint."""

    class MockResponse:
        status_code = 200

        def json(self):
            return {
                "scoring_settings": {
                    "pass_yd": 0.04,
                    "pass_td": 4,
                    "rec": 0.5,
                    "fum_lost": -2
                }
            }

    return MockResponse()


@pytest.fixture
def mock_api_error_response():
    """A mock error response from any Sleeper API endpoint."""

    class MockResponse:
        status_code = 404

        def raise_for_status(self):
            raise requests.exceptions.HTTPError("404 Client Error")


    return MockResponse()


@pytest.fixture
def mock_ff_playerids():
    """A mock DataFrame from nflreadpy.load_ff_playerids."""
    # Ensure fantasypros_id is Int64 to match the schema defined in get_league_info
    return pl.DataFrame(
        {"sleeper_id": [1049, 4034, 515, 223, 7523],
         "fantasypros_id": [9001, 9002, 9003, 9004, 9005],
         "gsis_id": ['00-1', '00-2', '00-3', '00-4', '00-5']},
        schema={"sleeper_id": pl.Int64, "fantasypros_id": pl.Int64, "gsis_id": pl.String}
    )


# --- Unit Tests ---

def test_translate_owner_id_success(mocker, mock_sleeper_users_response):
    """
    Tests that translate_owner_id correctly processes a successful API response.
    """
    # Arrange: Mock requests.get to return our sample user data
    mocker.patch('requests.get', return_value=mock_sleeper_users_response)

    # Act: Call the function
    result_df = translate_owner_id("dummy_league_id")

    # Assert: Check if the output is correct
    expected_df = pl.DataFrame({
        "owner_id": ["123", "456"],
        "owner_name": ["UserOne", "UserTwo"]
    })
    assert_frame_equal(result_df, expected_df)


def test_translate_owner_id_api_error(mocker, mock_api_error_response):
    """
    Tests that translate_owner_id raises an exception on API error.
    """
    # Arrange: Mock requests.get to return a 404 error
    mocker.patch('requests.get', return_value=mock_api_error_response)

    # Act & Assert: Check that the function raises an Exception
    with pytest.raises(requests.exceptions.HTTPError):
        translate_owner_id("invalid_league_id")


def test_get_scoring_weights_success(mocker, mock_sleeper_league_response):
    """
    Tests that get_scoring_weights correctly extracts the scoring dictionary.
    """
    # Arrange
    mocker.patch('requests.get', return_value=mock_sleeper_league_response)

    # Act
    result_dict = get_scoring_weights("dummy_league_id")

    # Assert
    expected_dict = {
        "pass_yd": 0.04,
        "pass_td": 4,
        "rec": 0.5,
        "fum_lost": -2
    }
    assert result_dict == expected_dict

def test_get_scoring_weights_api_error(mocker, mock_api_error_response):
    """
    Tests that get_scoring_weights raises an exception on API error.
    """
    # Arrange: Mock requests.get to return a 404 error
    mocker.patch('requests.get', return_value=mock_api_error_response)

    # Act & Assert: Check that the function raises an Exception
    with pytest.raises(requests.exceptions.HTTPError):
        get_scoring_weights("invalid_league_id")


def test_get_league_info_success(mocker, mock_sleeper_rosters_response, mock_sleeper_users_response, mock_ff_playerids):
    """
    Tests the main get_league_info function on a successful run.
    This test mocks all external dependencies.
    """
    # We need to mock multiple calls
    # 1. The call to get rosters
    # 2. The call to get player IDs
    # 3. The call to get users (inside translate_owner_id)
    mocker.patch('requests.get').side_effect = [mock_sleeper_rosters_response, mock_sleeper_users_response]
    mocker.patch('src.league.load_ff_playerids', return_value=mock_ff_playerids)

    result_df = get_league_info("dummy_league_id")

    # Check that the 'sleeper_ids' list was combined correctly
    owner_123_roster = result_df.filter(pl.col('owner_id') == '123')['sleeper_ids'][0]
    assert set(owner_123_roster) == {1049, 4034, 223, 7523}

    # Check that the 'fantasypros_ids' were mapped correctly
    owner_123_fp_ids = result_df.filter(pl.col('owner_id') == '123')['fantasypros_ids'][0]
    assert set(owner_123_fp_ids) == {9001, 9002, 9004, 9005}

    # Check that the 'gsis_ids' were mapped correctly
    owner_123_gsis_ids = result_df.filter(pl.col('owner_id') == '123')['gsis_ids'][0]
    assert set(owner_123_gsis_ids) == {'00-1', '00-2', '00-4', '00-5'}

    # Check the final DataFrame
    expected_df = pl.DataFrame(
        {
            "owner_id": ["123", "456"],
            "owner_name": ["UserOne", "UserTwo"],
            "sleeper_ids": [[1049, 4034, 223, 7523], [515]],
            "fantasypros_ids": [[9001, 9002, 9004, 9005], [9003]],
            "gsis_ids": [['00-1', '00-2', '00-4', '00-5'], ['00-3']]
        },
        schema_overrides={"sleeper_ids": pl.List(pl.Int64), "fantasypros_ids": pl.List(pl.Int64)}
    )
    assert_frame_equal(result_df, expected_df)

def test_get_league_info_api_error(mocker, mock_api_error_response):
    """
    Tests that get_league_info raises an exception on API error.
    """
    # Arrange: Mock requests.get to return a 404 error
    mocker.patch('requests.get', return_value=mock_api_error_response)

    # Act & Assert: Check that the function raises an Exception
    with pytest.raises(requests.exceptions.HTTPError):
        get_league_info("invalid_league_id")
