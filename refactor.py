import re
import os

with open('main.py', 'r', encoding='utf-8') as f:
    text = f.read()

# We want to extract EVERYTHING from 'class GameView(arcade.View):' until 'class MenuView(arcade.View):'
match = re.search(r'(class GameView\(arcade\.View\):.*?)(?=class MenuView\(arcade\.View\):)', text, flags=re.DOTALL)
if match:
    game_view_code = match.group(1)
    
    # We already have a skeleton definition in views/game_view.py with our imports.
    # We will append the body of GameView class to it, except we replace the skeleton `class GameView` with the real one.
    
    with open('views/game_view.py', 'r', encoding='utf-8') as f:
        gv_text = f.read()

    # Find where the skeleton class GameView starts
    skel_idx = gv_text.find('class GameView(arcade.View):')
    header_imports = gv_text[:skel_idx]
    
    # Write the combined file
    with open('views/game_view.py', 'w', encoding='utf-8') as f:
        f.write(header_imports)
        f.write("\n")
        f.write(game_view_code)

# Now what about main.py? We need to overwrite it to use the new modular system.
main_py_new = """import arcade
import os
import sys

# Ensure this directory is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.constants import SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE
from core.settings import GameSettings
from core.arcade_patch import apply_patches
from views.menu_view import MenuView
from views.transitions import MorphTransitionView
from loading_animation import LoadingView as _AnimLoadingView

def main():
    apply_patches()
    settings = GameSettings.load()
    window   = arcade.Window(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE, resizable=False)
    window.background_color = arcade.color.BLACK

    menu_view = MenuView(settings)

    def on_loading_complete():
        window.show_view(menu_view)

    loading_view = _AnimLoadingView(target_view=menu_view, next_view_fn=on_loading_complete)
    window.show_view(loading_view)
    arcade.run()

if __name__ == "__main__":
    main()
"""

with open('main.py', 'w', encoding='utf-8') as f:
    f.write(main_py_new)

print("Extraction and refactor complete.")
