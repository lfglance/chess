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
import time
from datetime import datetime

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

    def fetch_all_games(self, batch_size: int = 30, delay_between_batches: float = 1.0) -> list:
        """
        Fetch all games for the user in batches with rate limiting.
        
        Args:
            batch_size: Number of games to fetch per batch (max 30)
            delay_between_batches: Delay in seconds between batch requests
        """
        if batch_size > 30:
            batch_size = 30
            print("Warning: batch_size reduced to 30 (API limit)")
        
        all_games = []
        batch_num = 1
        last_timestamp = None
        
        print(f"Starting to fetch all games in batches of {batch_size}...")
        print(f"Rate limiting: {delay_between_batches}s delay between requests")
        
        while True:
            print(f"\n--- Batch {batch_num} ---")
            
            # Fetch batch with timestamp filter to avoid duplicates
            batch_games = self.fetch_games(
                max_games=batch_size,
                until=last_timestamp  # Fetch games older than the last game from previous batch
            )
            
            if not batch_games:
                print("No more games found. Finished fetching all games.")
                break
            
            # Add games to our collection
            all_games.extend(batch_games)
            
            # Update timestamp for next batch (use oldest game's timestamp)
            last_timestamp = batch_games[-1].get('createdAt')
            
            print(f"Fetched {len(batch_games)} games in batch {batch_num}")
            print(f"Total games collected so far: {len(all_games)}")
            
            if last_timestamp:
                readable_date = datetime.fromtimestamp(last_timestamp / 1000).strftime('%Y-%m-%d %H:%M:%S')
                print(f"Oldest game in this batch: {readable_date}")
            
            # If we got fewer games than requested, we've reached the end
            if len(batch_games) < batch_size:
                print("Received fewer games than requested. Reached end of games list.")
                break
            
            # Rate limiting: wait before next request
            if delay_between_batches > 0:
                print(f"Waiting {delay_between_batches}s before next batch...")
                time.sleep(delay_between_batches)
            
            batch_num += 1
        
        print(f"\n✓ Finished fetching all games. Total: {len(all_games)} games")
        return all_games

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

        # Fetch all games with batching and rate limiting
        print("\nFetching all games...")
        games = fetcher.fetch_all_games(batch_size=30, delay_between_batches=1.0)

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