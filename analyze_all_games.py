#!/usr/bin/env python3
"""
Analyze All Chess Games Script

Iterates through all games in lichess_games.json and analyzes them using Ollama
with streaming output to show the analysis progress in real-time.
"""

import json
import requests
import os
import sys
import time
from typing import List, Dict, Optional
from datetime import datetime
from game_analyzer import analyze_games_from_file, GameInfo, OllamaAnalyzer

class StreamingOllamaAnalyzer(OllamaAnalyzer):
    """Extended OllamaAnalyzer with streaming support and debug logs."""
    
    def analyze_game_streaming(self, game: GameInfo, username: str, model: str = "llama3.2:1b") -> Optional[str]:
        """
        Analyze game with streaming output and debug logs.
        
        Args:
            game: GameInfo object containing game data
            username: Username of the player to analyze
            model: Ollama model to use for analysis
        
        Returns:
            Complete analysis text from the LLM or None if failed
        """
        if not self.test_connection():
            return None
        
        prompt = self.format_game_for_analysis(game, username)
        
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": True  # Enable streaming
        }
        
        print(f"\n🔍 Starting analysis for game {game.game_id}")
        print(f"📡 Model: {model}")
        print(f"🎯 Player: {username} vs {game.black_player if game.white_player.lower() == username.lower() else game.white_player}")
        print(f"♟️  Opening: {game.opening_name}")
        print(f"⏱️  Time Control: {game.time_control}")
        print(f"📊 Total Moves: {game.total_moves}")
        print("=" * 80)
        print("🤖 Ollama Response Stream:")
        print("-" * 40)
        
        try:
            response = requests.post(
                self.api_url,
                json=payload,
                timeout=300,  # Longer timeout for streaming
                stream=True
            )
            response.raise_for_status()
            
            full_analysis = ""
            
            # Process streaming response
            for line in response.iter_lines(decode_unicode=True):
                if line.strip():
                    try:
                        chunk_data = json.loads(line)
                        if 'response' in chunk_data:
                            chunk_text = chunk_data['response']
                            # Print chunk in real-time with streaming effect
                            print(chunk_text, end='', flush=True)
                            full_analysis += chunk_text
                        
                        # Check if this is the final chunk
                        if chunk_data.get('done', False):
                            print()  # New line after streaming completes
                            break
                            
                    except json.JSONDecodeError as e:
                        print(f"\n⚠️  JSON decode error: {e}")
                        continue
            
            print("\n" + "=" * 80)
            print(f"✅ Analysis completed for game {game.game_id}")
            print(f"📄 Analysis length: {len(full_analysis)} characters")
            
            return full_analysis if full_analysis.strip() else None
            
        except requests.exceptions.RequestException as e:
            print(f"\n❌ Failed to analyze game: {e}")
            return None
        except Exception as e:
            print(f"\n❌ Unexpected error during analysis: {e}")
            return None
    
    def analyze_game_with_streaming_cache(self, game: GameInfo, username: str, model: str = "llama3.2:1b", force_refresh: bool = False) -> Optional[str]:
        """
        Analyze game with streaming support and caching.
        
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
                print(f"💾 Using cached analysis for game {game.game_id}")
                return cached_analysis['analysis']
        
        # Generate new analysis with streaming
        analysis = self.analyze_game_streaming(game, username, model)
        
        # Cache the result if successful
        if analysis:
            self.save_analysis_to_cache(game.game_id, model, username, analysis, game)
        
        return analysis

def analyze_all_games(
    username: str = "lza808",
    model: str = "llama3.2:1b",
    max_games: Optional[int] = None,
    force_refresh: bool = False,
    start_from: Optional[str] = None,
    delay_between_games: float = 2.0
) -> Dict[str, any]:
    """
    Analyze all games with streaming output and progress tracking.
    
    Args:
        username: Username of the player to analyze
        model: Ollama model to use for analysis
        max_games: Maximum number of games to analyze (None for all)
        force_refresh: If True, bypass cache for all games
        start_from: Game ID to start from (useful for resuming)
        delay_between_games: Seconds to wait between game analyses
    
    Returns:
        Dictionary with analysis results and statistics
    """
    print("🏁 Starting bulk game analysis")
    print("=" * 50)
    
    # Load all games
    games = analyze_games_from_file()
    if not games:
        print("❌ No games found. Make sure lichess_games.json exists.")
        return {"error": "No games found"}
    
    print(f"📚 Loaded {len(games)} games total")
    
    # Filter games if start_from is specified
    if start_from:
        start_index = next((i for i, g in enumerate(games) if g.game_id == start_from), 0)
        games = games[start_index:]
        print(f"🔄 Starting from game {start_from} (position {start_index + 1})")
    
    # Limit games if specified
    if max_games and max_games > 0:
        games = games[:max_games]
        print(f"🎯 Limited to {len(games)} games")
    
    # Initialize analyzer
    analyzer = StreamingOllamaAnalyzer()
    
    # Test connection
    print(f"\n🔌 Testing Ollama connection...")
    if not analyzer.test_connection():
        print("❌ Cannot connect to Ollama. Make sure it's running.")
        return {"error": "Ollama connection failed"}
    
    print("✅ Connected to Ollama successfully")
    print(f"🤖 Using model: {model}")
    print(f"⏱️  Delay between games: {delay_between_games}s")
    
    # Analysis statistics
    stats = {
        "total_games": len(games),
        "successful_analyses": 0,
        "failed_analyses": 0,
        "cached_analyses": 0,
        "start_time": datetime.now(),
        "analyzed_games": []
    }
    
    print(f"\n🚀 Beginning analysis of {len(games)} games...")
    print("=" * 80)
    
    for i, game in enumerate(games, 1):
        print(f"\n📋 GAME {i}/{len(games)}")
        print(f"🆔 Game ID: {game.game_id}")
        
        # Check if already cached (unless force refresh)
        is_cached = False
        if not force_refresh:
            cached = analyzer.load_analysis_from_cache(game.game_id, model, username)
            is_cached = cached is not None
        
        try:
            analysis = analyzer.analyze_game_with_streaming_cache(
                game, username, model, force_refresh
            )
            
            if analysis:
                stats["successful_analyses"] += 1
                if is_cached:
                    stats["cached_analyses"] += 1
                
                # Store game info for final report
                stats["analyzed_games"].append({
                    "game_id": game.game_id,
                    "opening": game.opening_name,
                    "result": game.winner or "draw",
                    "total_moves": game.total_moves,
                    "analysis_length": len(analysis),
                    "was_cached": is_cached
                })
                
                print(f"✅ Successfully analyzed game {i}/{len(games)}")
            else:
                stats["failed_analyses"] += 1
                print(f"❌ Failed to analyze game {i}/{len(games)}")
        
        except Exception as e:
            stats["failed_analyses"] += 1
            print(f"❌ Error analyzing game {game.game_id}: {e}")
        
        # Progress update
        remaining = len(games) - i
        if remaining > 0:
            print(f"📊 Progress: {i}/{len(games)} ({i/len(games)*100:.1f}%) | {remaining} games remaining")
            
            # Delay before next game (except for last game)
            if delay_between_games > 0:
                print(f"⏸️  Waiting {delay_between_games}s before next game...")
                time.sleep(delay_between_games)
    
    # Final statistics
    stats["end_time"] = datetime.now()
    stats["total_duration"] = stats["end_time"] - stats["start_time"]
    
    print("\n" + "=" * 80)
    print("🏆 BULK ANALYSIS COMPLETED!")
    print("=" * 80)
    print(f"📊 Total Games Processed: {stats['total_games']}")
    print(f"✅ Successful Analyses: {stats['successful_analyses']}")
    print(f"❌ Failed Analyses: {stats['failed_analyses']}")
    print(f"💾 Cached Analyses Used: {stats['cached_analyses']}")
    print(f"🆕 New Analyses Generated: {stats['successful_analyses'] - stats['cached_analyses']}")
    print(f"⏱️  Total Duration: {stats['total_duration']}")
    
    if stats["successful_analyses"] > 0:
        avg_duration = stats["total_duration"].total_seconds() / stats["successful_analyses"]
        print(f"📈 Average Time per Analysis: {avg_duration:.1f} seconds")
    
    return stats

def main():
    """Main function with command line argument handling."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Analyze all chess games with Ollama")
    parser.add_argument("--username", default="lza808", help="Username to analyze games for")
    parser.add_argument("--model", default="llama3.2:1b", help="Ollama model to use")
    parser.add_argument("--max-games", type=int, help="Maximum number of games to analyze")
    parser.add_argument("--force-refresh", action="store_true", help="Force refresh all analyses (bypass cache)")
    parser.add_argument("--start-from", help="Game ID to start analysis from")
    parser.add_argument("--delay", type=float, default=2.0, help="Delay between games in seconds")
    
    args = parser.parse_args()
    
    # Run the analysis
    stats = analyze_all_games(
        username=args.username,
        model=args.model,
        max_games=args.max_games,
        force_refresh=args.force_refresh,
        start_from=args.start_from,
        delay_between_games=args.delay
    )
    
    if "error" in stats:
        sys.exit(1)
    else:
        print(f"\n💾 Analysis cache directory: analysis_cache/")
        print(f"🌐 View results in Flask app: python app.py")
        sys.exit(0)

if __name__ == "__main__":
    main()