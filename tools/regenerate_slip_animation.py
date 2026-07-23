from __future__ import annotations

from pathlib import Path
import sys


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_DIR = PROJECT_ROOT / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from dynamic_ac_generator.animation import generate_rotor_reference_slip_animation
from dynamic_ac_generator.config import SimulationConfig
from dynamic_ac_generator.simulation import DynamicSimulation


def main() -> None:
    """Regenerate only the rotor-reference slip GIF and MP4 outputs."""
    config = SimulationConfig()
    results = DynamicSimulation(config).run()
    output_path = generate_rotor_reference_slip_animation(
        results,
        PROJECT_ROOT / "results" / "animations",
    )
    print(f"Saved {output_path}")
    print(f"Saved {output_path.with_suffix('.mp4')}")


if __name__ == "__main__":
    main()
