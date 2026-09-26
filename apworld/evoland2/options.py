from dataclasses import dataclass

from Options import Choice, OptionGroup, PerGameCommonOptions, Range


class Goal(Choice):
    """What you need to do to win.

    final_boss: defeat the final boss.
    final_boss_and_stars: same, but the way to the final boss stays blocked in game until you have
    collected the number of Stars set in "Stars Required"."""
    display_name = "Goal"
    option_final_boss = 0
    option_final_boss_and_stars = 1
    default = 0


class StarsRequired(Range):
    """Number of Stars needed to face the final boss when the goal is "final_boss_and_stars"."""
    display_name = "Stars Required"
    range_start = 1
    range_end = 30
    default = 15


evoland2_option_groups = [
    OptionGroup("Goal", [Goal, StarsRequired]),
]


@dataclass
class Evoland2Options(PerGameCommonOptions):
    goal: Goal
    stars_required: StarsRequired
