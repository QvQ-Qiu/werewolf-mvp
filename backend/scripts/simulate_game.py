"""完整一局模拟脚本（无 AI，固定随机种子）"""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path

# 允许从 backend/ 目录直接运行
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.game.simulator import create_test_engine, run_until_end
from app.models.game import Role


def main() -> None:
    parser = argparse.ArgumentParser(description="模拟十人狼人杀一局")
    parser.add_argument("--seed", type=int, default=42, help="随机种子")
    args = parser.parse_args()

    engine = create_test_engine(seed=args.seed)
    rng = random.Random(args.seed)
    state = run_until_end(engine, rng, max_rounds=30)

    print(f"=== 模拟对局 seed={args.seed} ===")
    print(f"胜者: {state.winner.value if state.winner else '无'}")
    print(f"天数: {state.day_number}")
    print("\n--- 最终身份 ---")
    for p in sorted(state.players, key=lambda x: x.seat):
        status = "存活" if p.is_alive else "死亡"
        role_name = {
            Role.WOLF: "狼人",
            Role.SEER: "预言家",
            Role.WITCH: "女巫",
            Role.HUNTER: "猎人",
            Role.GUARD: "守卫",
            Role.VILLAGER: "村民",
        }[p.role]
        human = " (玩家)" if p.is_human else ""
        print(f"  {p.seat}号 {p.name}{human}: {role_name} [{status}]")

    print("\n--- 公屏日志（最近 15 条）---")
    for entry in state.public_log[-15:]:
        seat = f"{entry.seat}号 " if entry.seat else ""
        print(f"  [{entry.type}] {seat}{entry.content}")


if __name__ == "__main__":
    main()
