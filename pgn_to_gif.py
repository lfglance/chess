import chess
import chess.pgn
import chess.svg
import io
from PIL import Image
import imageio
import os

def pgn_to_gif_or_video(pgn_file, output_file, output_format="gif", fps=1):
    """
    Convert a PGN file to a GIF or MP4 video of the chess game.

    Args:
        pgn_file (str): Path to the input PGN file.
        output_file (str): Path to save the output GIF or MP4.
        output_format (str): 'gif' or 'mp4' to specify output type.
        fps (int): Frames per second for the animation (controls speed).
    """
    # Read the PGN file
    with open(pgn_file, 'r') as pgn:
        game = chess.pgn.read_game(pgn)

    if game is None:
        raise ValueError("No valid game found in the PGN file.")

    # Initialize the board
    board = game.board()
    images = []

    # Iterate through all moves in the game
    for move in game.mainline_moves():
        # Make the move on the board
        board.push(move)

        # Generate SVG for the current board position
        svg_data = chess.svg.board(board=board, size=400)

        # Convert SVG to PNG using Pillow
        svg_bytes = io.BytesIO(svg_data.encode('utf-8'))
        img = Image.open(svg_bytes)

        # Convert to RGB (required for GIF/MP4)
        img = img.convert('RGB')
        images.append(img)

    # Ensure output format is valid
    if output_format not in ["gif", "mp4"]:
        raise ValueError("Output format must be 'gif' or 'mp4'.")

    # Save the images as GIF or MP4
    if output_format == "gif":
        images[0].save(
            output_file,
            save_all=True,
            append_images=images[1:],
            duration=1000//fps,  # Duration per frame in milliseconds
            loop=0  # Loop forever
        )
    elif output_format == "mp4":
        # Convert PIL images to numpy arrays for imageio
        images_np = [np.array(img) for img in images]
        imageio.mimwrite(output_file, images_np, fps=fps, macro_block_size=1)

    print(f"Successfully created {output_file}")

def main():
    # Example usage
    pgn_file = "game.pgn"  # Replace with your PGN file path
    output_file = "chess_game.gif"  # Output file (change to .mp4 for video)
    output_format = "gif"  # Change to "mp4" for video output
    fps = 1  # Adjust speed of animation (frames per second)

    try:
        pgn_to_gif_or_video(pgn_file, output_file, output_format, fps)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()