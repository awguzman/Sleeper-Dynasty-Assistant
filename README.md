# Sleeper Dynasty Assistant

An interactive web dashboard for your Sleeper-based dynasty and in-season fantasy football leagues. This application 
fetches live data from [nflreadpy](https://github.com/nflverse/nflreadpy) and integrates it with your specific league's 
rosters via [Sleeper.com API](https://docs.sleeper.com/).

You can test out an online version of the application via the link: https://sleeper-dynasty-assistant.onrender.com

Note: This web version is VERY slow due to the free-tier limitations of render.com. It should be viewed more as a demo.

## Features

The dashboard is organized into two main sections: **Draft Tools** and **In-Season Tools**.

### Core Functionality
- **League-Aware Analysis**: Enter your Sleeper League ID to unlock features like player ownership tracking and filtering for free agents.
- **Default Mode**: The app is fully functional even without a League ID, providing general rankings and visualizations.
- **High-Performance Backend**: Utilizes `Polars` for fast data processing and `Dash` for efficient data caching.
- **Live Data**: Player rankings and projections are fetched from `nflreadpy`, ensuring the data is up-to-date.

### Draft Tools
- **Dynasty Draft Board**: A sortable and filterable table showing dynasty rankings (ECR), player age, and ownership status.
- **Draft Tiers**: An interactive visualization that groups players into statistically distinct tiers based on their ECR ranks. This helps identify value drop-offs at each position.
- **Dynasty Trade Values**: Side-by-side, scrollable tables displaying player trade values for each position.
- **Season Efficiency**: A scatter plot showing actual vs. expected fantasy points for a player over the previous season. Used to spot scoring regression candidates for the next season.

### In-Season Tools
- **Weekly Projections**: A table displaying weekly positional rankings, ECR, and start/sit grades to help with lineup decisions.
- **Weekly Tiers**: A similar tier chart to above tailored for weekly rankings.
- **Last Season Efficiency**: An interactive scatter plot showing actual vs. expected fantasy points for the previous season, helping identify over/under-performers.
- **Weekly Efficiency**: A scatter plot showing actual vs. expected fantasy points for the most recent week. Used to spot efficiency trends throughout the season.

## Packages/Frameworks

- **Dashboard & Visualizations**: Dash, Plotly
- **Data Pipeline**: Polars
- **Data Source**: nflreadpy, Sleeper API
- **Machine Learning**: scikit-learn

## Setup and Local Installation

To run the dashboard on your local machine, follow these steps.

1.  **Clone the Repository**
    ```sh
    git clone https://github.com/your-username/Sleeper-Dynasty-Assistant.git
    cd Sleeper-Dynasty-Assistant
    ```

2.  **Create and Activate a Virtual Environment** (Recommended)
    ```sh
    # Windows
    python -m venv .venv
    .venv\Scripts\activate

    # macOS/Linux
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3.  **Install Dependencies**
    Install all required packages from the `requirements.txt` file.
    ```sh
    pip install -r requirements.txt
    ```

4.  **Run the Application**
    Execute the `dashboard.py` script. The application will be available at `http://127.0.0.1:8050/` in your web browser.
    ```sh
    python dashboard.py
    ```

## Usage

1.  Upon loading, the dashboard will display general, non-league-specific rankings and visualizations.
2.  To enable league-specific features, enter your Sleeper League ID in the input box at the top and press Enter.
3.  Once the league data is loaded, the "Select Owner" dropdown and "Show Taken Players" checkboxes will become active.
4.  Select your owner name to enable ownership-based filtering and styling.
5.  Navigate through the nested tabs to explore the different tools available.

## Future Additions 

This is a living project with many planned features including:

- **League View**: A "bird's-eye view" tab that displays all team rosters in the league side-by-side with strength analysis.
- **In-house Projections** Use historical data to produce custom scoring projections. XGBoost based?
