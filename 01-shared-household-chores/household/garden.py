"""Garden progression derived from a member's lifetime XP."""

from typing import NamedTuple


class GardenStage(NamedTuple):
    """A garden stage and the lifetime XP at which it begins."""

    threshold: int
    identifier: str
    label: str


GARDEN_STAGES = (
    GardenStage(0, "empty_soil", "Empty soil"),
    GardenStage(25, "seed", "Seed"),
    GardenStage(75, "sprout", "Sprout"),
    GardenStage(150, "small_plant", "Small plant"),
    GardenStage(300, "flowers", "Flowers"),
    GardenStage(500, "bushes", "Bushes"),
    GardenStage(800, "tree", "Tree"),
    GardenStage(1200, "richer_garden", "Richer garden"),
)


def calculate_garden_stage(lifetime_xp: int) -> GardenStage:
    """Return the stage reached by a non-negative whole-number XP total."""

    if not isinstance(lifetime_xp, int) or isinstance(lifetime_xp, bool):
        raise TypeError("lifetime_xp must be an integer")
    if lifetime_xp < 0:
        raise ValueError("lifetime_xp must be non-negative")

    for stage in reversed(GARDEN_STAGES):
        if lifetime_xp >= stage.threshold:
            return stage

    raise AssertionError("the zero-XP garden stage is missing")
