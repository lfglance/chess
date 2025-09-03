#!/usr/bin/env python3
"""
Lichess Games Fetcher

A script to authenticate to the Lichess API and retrieve all games for a user.
Usage: uv run python lichess_games.py
"""

import os
import sys
import requests
from typing import Optional
import json

class LichessGamesFetcher:
    def __init__(self, api_token: Optional[str] = None):
        """Initialize the Lichess games fetcher with API token."""
        # self.api_token = api_token or os.getenv('LICHESS_API_TOKEN')
        self.base_url = "https://lichess.org/api"
        self.username = "lza808"

        # if not self.api_token:
        #     raise ValueError("API token is required. Set LICHESS_API_TOKEN environment variable or pass it directly.")

    def get_headers(self) -> dict:
        """Get headers for API requests."""
        return {
            "Accept": "application/x-ndjson"  # Use ND-JSON for streaming
        }

    # def test_auth(self) -> bool:
    #     """Test API authentication by fetching account info."""
    #     try:
    #         response = requests.get(
    #             f"{self.base_url}/account",
    #             headers=self.get_headers(),
    #             timeout=10
    #         )
    #         response.raise_for_status()
    #         account_info = response.json()
    #         print(f"✓ Authentication successful. Logged in as: {account_info.get('username', 'Unknown')}")
    #         return True
    #     except requests.exceptions.RequestException as e:
    #         print(f"✗ Authentication failed: {e}")
    #         return False

    def fetch_games(self, max_games: Optional[int] = 30, since: Optional[int] = None, until: Optional[int] = None) -> list:
        """
        Fetch games for the user.

        Args:
            max_games: Maximum number of games to fetch
            since: Timestamp in milliseconds to fetch games since
            until: Timestamp in milliseconds to fetch games until
        """
        url = f"{self.base_url}/games/user/{self.username}"

        params = {}
        if max_games:
            params['max'] = max_games
        if since:
            params['since'] = since
        if until:
            params['until'] = until
        params['accuracy'] = True
        params['opening'] = True

        print(f"Fetching games from: {url}")
        if params:
            print(f"Parameters: {params}")

        try:
            response = requests.get(
                url,
                headers=self.get_headers(),
                params=params,
                timeout=30,
                stream=True
            )
            response.raise_for_status()

            games = []
            for line in response.iter_lines(decode_unicode=True):
                if line.strip():
                    try:
                        game = json.loads(line)
                        games.append(game)
                    except json.JSONDecodeError:
                        print(f"Warning: Could not parse line: {line[:100]}...")
                        continue

            print(f"✓ Successfully fetched {len(games)} games")
            return games

        except requests.exceptions.RequestException as e:
            print(f"✗ Failed to fetch games: {e}")
            return []

    def save_games_to_file(self, games: list, filename: str = "lichess_games.json"):
        """Save games to a JSON file."""
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(games, f, indent=2, ensure_ascii=False)
            print(f"✓ Games saved to {filename}")
        except Exception as e:
            print(f"✗ Failed to save games: {e}")

def main():
    """Main function to run the script."""
    print("Lichess Games Fetcher")
    print("=" * 30)

    # Get API token from environment or prompt user
    # api_token = os.getenv('LICHESS_API_TOKEN')
    # if not api_token:
    #     print("API token not found in environment variables.")
    #     print("Please set LICHESS_API_TOKEN environment variable with your Lichess API token.")
    #     print("You can generate one at: https://lichess.org/account/OAuth/token")
    #     return 1

    try:
        # Initialize fetcher
        fetcher = LichessGamesFetcher()

        # Test authentication
        # if not fetcher.test_auth():
        #     return 1

        # Fetch all games (you can modify this to add limits)
        print("\nFetching games...")
        games = fetcher.fetch_games()

        if games:
            # Save to file
            fetcher.save_games_to_file(games)

            # Print some basic stats
            print(f"\nGame Statistics:")
            print(f"Total games: {len(games)}")
            if games:
                print(f"Latest game: {games[0].get('createdAt', 'Unknown')}")
                print(f"Oldest game: {games[-1].get('createdAt', 'Unknown')}")

        return 0

    except Exception as e:
        print(f"✗ Error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())