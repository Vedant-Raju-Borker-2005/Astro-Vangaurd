# AstroVanguard: AI Tactical Space Siege — Enhanced v5.0

AstroVanguard is an action-packed, fast-paced 2D tactical space shooter built with Python and the [Arcade library](https://api.arcade.academy/en/latest/). Defend your sector against relentless AI-driven enemy waves, defeat challenging bosses, and upgrade your ship to survive the siege!

## 🚀 Features

*   **Intense Wave-Based Combat**: Battle through dynamic waves of enemies with various types (Scout, Soldier, Elite, Kamikaze, Sniper, Shielded).
*   **Boss Encounters**: Survive escalating waves to face off against formidable boss ships.
*   **Adaptive Wave Modifiers**: Waves can unpredictably feature modifiers like *Speed Rush*, *Elite Surge*, *Shielded Wave*, and *Dense Pack*.
*   **Upgrades & Power-ups**: Enhance your ship with multiple weapon types (Single, Spread, Piercing) and collect in-game power-ups (Shields, Nukes, Speed/Energy Boosts, Extra Lives).
*   **Advanced Player Mechanics**: Utilize your dash ability to evade incoming fire, manage your energy reserves, and rely on a regenerating energy shield.
*   **Combo & Achievement System**: Chain kills to build your combo multiplier for high scores and unlock in-game achievements.
*   **Flexible Controls**: Support for both Keyboard & Mouse and experimental Gesture controls.
*   **Multiple Difficulties**: Tailored experiences for all skill levels (Easy, Normal, Hard), modifying enemy health, speed, fire rates, and spawn dynamics.

## 🛠️ Prerequisites & Installation

1.  **Python 3.9+** is recommended.
2.  Clone the repository:
    ```bash
    git clone https://github.com/Vedant-Raju-Borker-2005/Astro-Vangaurd.git
    cd Astro-Vangaurd
    ```
    *(Or navigate to your local project directory)*
3.  Install the required dependencies:
    ```bash
    pip install arcade
    ```
    *(If there are additional libraries like OpenCV or MediaPipe for gesture controls, install those as well).*

## 🎮 How to Play

Run the main game script to launch AstroVanguard:

```bash
python main.py
```

### Default Controls (Keyboard & Mouse)
*   **Movement**: `W`, `A`, `S`, `D` (or Arrow Keys)
*   **Aim**: Mouse cursor
*   **Shoot**: Left Mouse Button (Hold for continuous fire depending on weapon)
*   **Dash**: `Space` (Consumes energy)
*   **Pause Game**: `Escape` or `P`

## 📂 Project Structure

```text
AstroVanguard/
├── main.py                 # Main entry point for the game
├── core/                   # Core mechanics, constants, settings, and patches
├── entities/               # Game entities (Player, Enemies, Bosses, VFX)
├── systems/                # Game systems (Wave Manager, Achievements, etc.)
├── ui/                     # User interface components and overlays
├── views/                  # Game states (Menu, Playing, Paused, Transitions)
├── assets/                 # Images, sounds, and music resources
└── saves/                  # Local save data (High scores, Settings)
```

## 🏆 Achievements

Test your skills and try to unlock all achievements:
*   *First Blood*: Get your first kill.
*   *Boss Slayer*: Defeat your first boss.
*   *Combo Master*: Reach 10x and 25x combo multipliers.
*   *Pacifist Wave*: Survive a wave without shooting.
*   *Sharpshooter*, *Dodger*, *Iron Shield*, and more!

## 📜 Credits

Developed by Vedant Raju Borkar.
Built using the Python [Arcade](https://api.arcade.academy/en/latest/) library.
