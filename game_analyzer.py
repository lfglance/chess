#!/usr/bin/env python3
"""
Chess Game Analyzer

Functions to extract and analyze chess game data from Lichess API responses.
"""

import json
import requests
import os
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from datetime import datetime

@dataclass
class GameInfo:
    """Structured representation of a chess game."""
    game_id: str
    winner: Optional[str]  # 'white', 'black', or None for draw
    white_player: str
    black_player: str
    white_rating: int
    black_rating: int
    moves: List[str]  # List of moves in algebraic notation
    opening_name: str
    opening_eco: str  # ECO code (e.g., "B10")
    game_status: str  # 'mate', 'resign', 'draw', etc.
    time_control: str  # e.g., "10+5" for 10 minutes + 5 second increment
    created_at: datetime
    total_moves: int

def extract_game_info(game_data: Dict[str, Any]) -> GameInfo:
    """
    Extract key information from a single Lichess game.
    
    Args:
        game_data: Dictionary containing game data from Lichess API
    
    Returns:
        GameInfo: Structured game information
    """
    # Extract winner
    winner = game_data.get('winner')  # 'white', 'black', or None
    
    # Extract players
    players = game_data.get('players', {})
    white_player = players.get('white', {}).get('user', {}).get('name', 'Unknown')
    black_player = players.get('black', {}).get('user', {}).get('name', 'Unknown')
    white_rating = players.get('white', {}).get('rating', 0)
    black_rating = players.get('black', {}).get('rating', 0)
    
    # Extract moves
    moves_string = game_data.get('moves', '')
    moves = moves_string.split() if moves_string else []
    
    # Extract opening information
    opening = game_data.get('opening', {})
    opening_name = opening.get('name', 'Unknown Opening')
    opening_eco = opening.get('eco', 'Unknown')
    
    # Extract game metadata
    game_id = game_data.get('id', 'Unknown')
    game_status = game_data.get('status', 'Unknown')
    created_at = datetime.fromtimestamp(game_data.get('createdAt', 0) / 1000)
    
    # Extract time control
    clock = game_data.get('clock', {})
    initial_time = clock.get('initial', 0) // 60  # Convert seconds to minutes
    increment = clock.get('increment', 0)
    time_control = f"{initial_time}+{increment}"
    
    return GameInfo(
        game_id=game_id,
        winner=winner,
        white_player=white_player,
        black_player=black_player,
        white_rating=white_rating,
        black_rating=black_rating,
        moves=moves,
        opening_name=opening_name,
        opening_eco=opening_eco,
        game_status=game_status,
        time_control=time_control,
        created_at=created_at,
        total_moves=len(moves)
    )

def analyze_games_from_file(filename: str = "lichess_games.json") -> List[GameInfo]:
    """
    Load and analyze all games from a JSON file.
    
    Args:
        filename: Path to the JSON file containing game data
    
    Returns:
        List of GameInfo objects
    """
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            games_data = json.load(f)
        
        return [extract_game_info(game) for game in games_data]
    
    except FileNotFoundError:
        print(f"Error: File {filename} not found")
        return []
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in {filename}")
        return []
    except Exception as e:
        print(f"Error analyzing games: {e}")
        return []

def print_game_summary(game: GameInfo) -> None:
    """Print a formatted summary of a game."""
    print(f"\n--- Game {game.game_id} ---")
    print(f"Players: {game.white_player} (White, {game.white_rating}) vs {game.black_player} (Black, {game.black_rating})")
    print(f"Winner: {game.winner or 'Draw'}")
    print(f"Opening: {game.opening_name} ({game.opening_eco})")
    print(f"Status: {game.game_status}")
    print(f"Time Control: {game.time_control}")
    print(f"Total Moves: {game.total_moves}")
    print(f"Date: {game.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"First 10 moves: {' '.join(game.moves[:10])}...")

def get_win_loss_stats(games: List[GameInfo], username: str) -> Dict[str, int]:
    """
    Calculate win/loss/draw statistics for a specific player.
    
    Args:
        games: List of GameInfo objects
        username: Username to calculate stats for
    
    Returns:
        Dictionary with 'wins', 'losses', 'draws' counts
    """
    wins = 0
    losses = 0
    draws = 0
    
    for game in games:
        if game.winner is None:
            draws += 1
        elif ((game.white_player.lower() == username.lower() and game.winner == 'white') or
              (game.black_player.lower() == username.lower() and game.winner == 'black')):
            wins += 1
        else:
            losses += 1
    
    return {'wins': wins, 'losses': losses, 'draws': draws}

class OllamaAnalyzer:
    """Integration with local Ollama instance for chess game analysis."""
    
    def __init__(self, ollama_url: str = "http://127.0.0.1:11434", cache_dir: str = "analysis_cache"):
        self.ollama_url = ollama_url
        self.api_url = f"{ollama_url}/api/generate"
        self.cache_dir = cache_dir
        
        # Create cache directory if it doesn't exist
        if not os.path.exists(self.cache_dir):
            os.makedirs(self.cache_dir)
    
    def test_connection(self) -> bool:
        """Test connection to Ollama instance."""
        try:
            response = requests.get(f"{self.ollama_url}/api/tags", timeout=5)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            print(f"✗ Failed to connect to Ollama: {e}")
            return False
    
    def format_game_for_analysis(self, game: GameInfo, username: str) -> str:
        """Format game data for LLM analysis."""
        user_color = "White" if game.white_player.lower() == username.lower() else "Black"
        opponent = game.black_player if user_color == "White" else game.white_player
        user_rating = game.white_rating if user_color == "White" else game.black_rating
        opponent_rating = game.black_rating if user_color == "White" else game.white_rating
        
        # Determine result from user's perspective
        if game.winner is None:
            result = "Draw"
        elif ((user_color == "White" and game.winner == "white") or 
              (user_color == "Black" and game.winner == "black")):
            result = "Win"
        else:
            result = "Loss"
        
        # Format moves in pairs for readability
        move_pairs = []
        for i in range(0, len(game.moves), 2):
            white_move = game.moves[i] if i < len(game.moves) else ""
            black_move = game.moves[i + 1] if i + 1 < len(game.moves) else ""
            move_num = (i // 2) + 1
            if black_move:
                move_pairs.append(f"{move_num}. {white_move} {black_move}")
            else:
                move_pairs.append(f"{move_num}. {white_move}")
        
        formatted_moves = " ".join(move_pairs)
        
        return f"""
Game Analysis Request:

Player: {username} (Rating: {user_rating})
Opponent: {opponent} (Rating: {opponent_rating})
Color: {user_color}
Result: {result}
Opening: {game.opening_name} ({game.opening_eco})
Game Status: {game.game_status}
Time Control: {game.time_control}
Total Moves: {game.total_moves}

Moves: {formatted_moves}

Please analyze this chess game and provide feedback on:
1. Key strategic decisions and turning points
2. Tactical mistakes or missed opportunities
3. Opening play evaluation
4. Endgame technique (if applicable)
5. Specific suggestions for improvement
6. Overall assessment of the player's performance

Focus on constructive feedback that will help the player improve their chess skills.
"""
    
    def analyze_game(self, game: GameInfo, username: str, model: str = "llama3.2") -> Optional[str]:
        """
        Send game data to Ollama for analysis.
        
        Args:
            game: GameInfo object containing game data
            username: Username of the player to analyze
            model: Ollama model to use for analysis
        
        Returns:
            Analysis text from the LLM or None if failed
        """
        if not self.test_connection():
            return None
        
        prompt = self.format_game_for_analysis(game, username)
        
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": False
        }
        
        try:
            print(f"Analyzing game {game.game_id} with {model}...")
            response = requests.post(
                self.api_url,
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            
            result = response.json()
            return result.get('response', 'No analysis returned')
            
        except requests.exceptions.RequestException as e:
            print(f"✗ Failed to analyze game: {e}")
            return None
        except json.JSONDecodeError:
            print("✗ Invalid response from Ollama")
            return None
    
    def get_cache_filename(self, game_id: str, model: str, username: str) -> str:
        """Generate cache filename for a game analysis."""
        safe_model = model.replace(":", "_").replace("/", "_")
        return os.path.join(self.cache_dir, f"{game_id}_{username}_{safe_model}.json")
    
    def save_analysis_to_cache(self, game_id: str, model: str, username: str, analysis: str, game_info: GameInfo) -> None:
        """Save analysis result to cache file."""
        cache_data = {
            "game_id": game_id,
            "model": model,
            "username": username,
            "analysis": analysis,
            "timestamp": datetime.now().isoformat(),
            "game_info": {
                "white_player": game_info.white_player,
                "black_player": game_info.black_player,
                "winner": game_info.winner,
                "opening_name": game_info.opening_name,
                "opening_eco": game_info.opening_eco,
                "total_moves": game_info.total_moves,
                "created_at": game_info.created_at.isoformat()
            }
        }
        
        cache_file = self.get_cache_filename(game_id, model, username)
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
            print(f"✓ Analysis cached to {cache_file}")
        except Exception as e:
            print(f"✗ Failed to cache analysis: {e}")
    
    def load_analysis_from_cache(self, game_id: str, model: str, username: str) -> Optional[Dict]:
        """Load analysis from cache if it exists."""
        cache_file = self.get_cache_filename(game_id, model, username)
        
        if not os.path.exists(cache_file):
            return None
        
        try:
            with open(cache_file, 'r', encoding='utf-8') as f:
                cache_data = json.load(f)
            print(f"✓ Loaded cached analysis from {cache_file}")
            return cache_data
        except Exception as e:
            print(f"✗ Failed to load cached analysis: {e}")
            return None
    
    def analyze_game_with_cache(self, game: GameInfo, username: str, model: str = "llama3.2:1b", force_refresh: bool = False) -> Optional[str]:
        """
        Analyze game with caching support.
        
        Args:
            game: GameInfo object containing game data
            username: Username of the player to analyze
            model: Ollama model to use for analysis
            force_refresh: If True, bypass cache and generate new analysis
        
        Returns:
            Analysis text from the LLM or cached result
        """
        # Try to load from cache first (unless force refresh)
        if not force_refresh:
            cached_analysis = self.load_analysis_from_cache(game.game_id, model, username)
            if cached_analysis:
                return cached_analysis['analysis']
        
        # Generate new analysis
        analysis = self.analyze_game(game, username, model)
        
        # Cache the result if successful
        if analysis:
            self.save_analysis_to_cache(game.game_id, model, username, analysis, game)
        
        return analysis

def analyze_game_with_llm(game_id: str, username: str = "lza808", model: str = "llama3.2:1b", force_refresh: bool = False) -> None:
    """
    Analyze a specific game using Ollama LLM with caching support.
    
    Args:
        game_id: ID of the game to analyze
        username: Username of the player
        model: Ollama model to use
        force_refresh: If True, bypass cache and generate new analysis
    """
    # Load games
    games = analyze_games_from_file()
    if not games:
        print("No games found")
        return
    
    # Find specific game
    game = next((g for g in games if g.game_id == game_id), None)
    if not game:
        print(f"Game {game_id} not found")
        return
    
    # Analyze with Ollama (with caching)
    analyzer = OllamaAnalyzer()
    analysis = analyzer.analyze_game_with_cache(game, username, model, force_refresh)
    
    if analysis:
        print(f"\n{'='*60}")
        print(f"GAME ANALYSIS - {game_id}")
        print(f"{'='*60}")
        print_game_summary(game)
        print(f"\n{'='*60}")
        print("LLM ANALYSIS:")
        print(f"{'='*60}")
        print(analysis)
    else:
        print("Failed to get analysis")

def list_cached_analyses(cache_dir: str = "analysis_cache") -> List[Dict]:
    """
    List all cached analysis files.
    
    Args:
        cache_dir: Directory containing cached analyses
    
    Returns:
        List of cached analysis metadata
    """
    if not os.path.exists(cache_dir):
        return []
    
    cached_analyses = []
    for filename in os.listdir(cache_dir):
        if filename.endswith('.json'):
            filepath = os.path.join(cache_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    cache_data = json.load(f)
                
                cached_analyses.append({
                    'filename': filename,
                    'game_id': cache_data.get('game_id'),
                    'model': cache_data.get('model'),
                    'username': cache_data.get('username'),
                    'timestamp': cache_data.get('timestamp'),
                    'opening': cache_data.get('game_info', {}).get('opening_name', 'Unknown')
                })
            except Exception as e:
                print(f"Warning: Could not read {filename}: {e}")
                continue
    
    return sorted(cached_analyses, key=lambda x: x['timestamp'] or '', reverse=True)

def show_cached_analyses() -> None:
    """Display all cached analyses in a readable format."""
    cached = list_cached_analyses()
    
    if not cached:
        print("No cached analyses found")
        return
    
    print(f"\nCached Analyses ({len(cached)} total):")
    print("=" * 60)
    
    for analysis in cached:
        timestamp = datetime.fromisoformat(analysis['timestamp']).strftime('%Y-%m-%d %H:%M:%S') if analysis['timestamp'] else 'Unknown'
        print(f"Game: {analysis['game_id']} | Model: {analysis['model']} | Player: {analysis['username']}")
        print(f"Opening: {analysis['opening']} | Analyzed: {timestamp}")
        print("-" * 40)

def main():
    """Example usage of the game analyzer."""
    print("Chess Game Analyzer")
    print("=" * 30)
    
    # Analyze games
    games = analyze_games_from_file()
    
    if not games:
        print("No games found or error loading games")
        return
    
    print(f"Loaded {len(games)} games")
    
    # Show first few games
    for i, game in enumerate(games[:3]):
        print_game_summary(game)
        if i < 2:
            print("-" * 50)
    
    # Show stats for lza808
    stats = get_win_loss_stats(games, "lza808")
    print(f"\nStats for lza808:")
    print(f"Wins: {stats['wins']}")
    print(f"Losses: {stats['losses']}")
    print(f"Draws: {stats['draws']}")
    
    # Show most common openings
    opening_counts = {}
    for game in games:
        opening_counts[game.opening_name] = opening_counts.get(game.opening_name, 0) + 1
    
    print(f"\nMost Common Openings:")
    for opening, count in sorted(opening_counts.items(), key=lambda x: x[1], reverse=True)[:5]:
        print(f"{opening}: {count} games")
    
    # Test Ollama connection
    print(f"\nTesting Ollama connection...")
    analyzer = OllamaAnalyzer()
    if analyzer.test_connection():
        print("✓ Ollama connection successful")
        print(f"\nTo analyze a specific game, use:")
        print(f"analyze_game_with_llm('{games[0].game_id}')")
        print(f"\nTo force refresh analysis:")
        print(f"analyze_game_with_llm('{games[0].game_id}', force_refresh=True)")
    else:
        print("✗ Ollama connection failed")
    
    # Show cached analyses
    show_cached_analyses()

if __name__ == "__main__":
    main()