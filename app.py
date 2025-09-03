#!/usr/bin/env python3
"""
Chess Games Flask Web App

A simple Flask web application to display and analyze chess games from Lichess.
"""

from flask import Flask, render_template, request
from game_analyzer import analyze_games_from_file, list_cached_analyses
from datetime import datetime
import markdown

app = Flask(__name__)

@app.route('/')
def index():
    """Main route showing all available games."""
    games = analyze_games_from_file()
    
    if not games:
        return render_template('error.html', 
                             error_message="No games found. Make sure lichess_games.json exists.")
    
    return render_template('games_list.html', games=games)

@app.route('/game/<game_id>')
def game_detail(game_id):
    """Show detailed view of a specific game."""
    games = analyze_games_from_file()
    game = next((g for g in games if g.game_id == game_id), None)
    
    if not game:
        return render_template('error.html', 
                             error_message=f"Game {game_id} not found.")
    
    return render_template('game_detail.html', game=game)

@app.route('/analyze/<game_id>')
def analyze_game(game_id):
    """Analyze a specific game with LLM."""
    model = request.args.get('model', 'llama3.2:1b')
    force_refresh = request.args.get('force_refresh', 'false').lower() == 'true'
    
    games = analyze_games_from_file()
    game = next((g for g in games if g.game_id == game_id), None)
    
    if not game:
        return render_template('error.html', 
                             error_message=f"Game {game_id} not found.")
    
    # Import here to avoid issues if Ollama is not available
    try:
        from game_analyzer import OllamaAnalyzer
        analyzer = OllamaAnalyzer()
        
        if not analyzer.test_connection():
            return render_template('error.html', 
                                 error_message="Cannot connect to Ollama. Make sure it's running on http://127.0.0.1:11434")
        
        analysis = analyzer.analyze_game_with_cache(game, "lza808", model, force_refresh)
        
        if not analysis:
            return render_template('error.html', 
                                 error_message="Failed to generate analysis.")
        
        # Convert markdown to HTML
        md = markdown.Markdown(extensions=['extra', 'codehilite'])
        analysis_html = md.convert(analysis)
        
        return render_template('game_analysis.html', 
                             game=game, 
                             analysis=analysis,
                             analysis_html=analysis_html,
                             model=model)
    
    except Exception as e:
        return render_template('error.html', 
                             error_message=f"Analysis error: {str(e)}")

@app.route('/cache')
def cached_analyses():
    """Show all cached analyses."""
    cached = list_cached_analyses()
    return render_template('cached_analyses.html', cached=cached)

@app.route('/stats')
def stats():
    """Show game statistics."""
    games = analyze_games_from_file()
    
    if not games:
        return render_template('error.html', 
                             error_message="No games found.")
    
    # Calculate stats
    wins = losses = draws = 0
    opening_counts = {}
    
    for game in games:
        # Count results
        if game.winner is None:
            draws += 1
        elif ((game.white_player.lower() == "lza808" and game.winner == "white") or
              (game.black_player.lower() == "lza808" and game.winner == "black")):
            wins += 1
        else:
            losses += 1
        
        # Count openings
        opening_counts[game.opening_name] = opening_counts.get(game.opening_name, 0) + 1
    
    # Sort openings by frequency
    top_openings = sorted(opening_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    
    stats_data = {
        'total_games': len(games),
        'wins': wins,
        'losses': losses,
        'draws': draws,
        'win_rate': round((wins / len(games)) * 100, 1) if games else 0,
        'top_openings': top_openings,
        'latest_game': games[0] if games else None,
        'oldest_game': games[-1] if games else None
    }
    
    return render_template('stats.html', stats=stats_data)

@app.template_filter('format_datetime')
def format_datetime(dt):
    """Template filter to format datetime objects."""
    if isinstance(dt, datetime):
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    return str(dt)

@app.template_filter('format_moves')
def format_moves(moves, limit=10):
    """Template filter to format move list."""
    if not moves:
        return "No moves"
    
    if len(moves) <= limit:
        return ' '.join(moves)
    else:
        return ' '.join(moves[:limit]) + f'... ({len(moves)} total moves)'

if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=5000)