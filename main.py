import arcade
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
