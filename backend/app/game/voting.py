"""投票逻辑：狼队票选与白天放逐投票"""

import random
from collections import Counter

from app.models.game import GameState, Player, WolfVote


def resolve_wolf_kill(state: GameState, rng: random.Random) -> int | None:
    """
    根据狼刀提名计算最终刀口。
    所有狼人（包括人类狼人）的票都计入有效票；平票随机选取。
    不允许空刀，必须已有 3 狼各提名 1 人。
    """
    nominations = state.night_actions.wolf_nominations
    wolves = state.alive_wolves()
    if len(wolves) == 0:
        return None

    votes: list[WolfVote] = []
    for wolf in wolves:
        target = nominations.get(wolf.seat)
        if target is None:
            continue
        votes.append(
            WolfVote(
                nominator_seat=wolf.seat,
                target_seat=target,
                is_effective=True,
            )
        )
    state.wolf_votes = votes

    targets = [v.target_seat for v in votes]
    if not targets:
        return None

    counts = Counter(targets)
    max_votes = max(counts.values())
    top_targets = [t for t, c in counts.items() if c == max_votes]
    return rng.choice(top_targets)


def tally_day_votes(state: GameState) -> tuple[int | None, dict[int, int], bool]:
    """
    统计白天投票。
    返回 (被放逐座位或 None, 票型统计, 是否平票)。
    平票：最高票 >= 2 人并列 → 无人出局。
    """
    vote_counts: Counter[int] = Counter()
    for record in state.day_votes:
        if record.target_seat is not None:
            vote_counts[record.target_seat] += 1

    if not vote_counts:
        return None, dict(vote_counts), False

    max_votes = max(vote_counts.values())
    top_targets = [t for t, c in vote_counts.items() if c == max_votes]

    if len(top_targets) >= 2:
        return None, dict(vote_counts), True

    return top_targets[0], dict(vote_counts), False


def format_vote_summary(vote_counts: dict[int, int], votes: list) -> str:
    """生成票型公布文案"""
    parts = []
    for record in votes:
        if record.target_seat is None:
            parts.append(f"{record.voter_seat}号弃票")
        else:
            parts.append(f"{record.voter_seat}号投{record.target_seat}号")
    summary = "；".join(parts)
    count_str = "，".join(f"{s}号得{c}票" for s, c in sorted(vote_counts.items()))
    if count_str:
        return f"{summary}。{count_str}"
    return summary


def get_alive_players(state: GameState) -> list[Player]:
    return [p for p in state.players if p.is_alive]
