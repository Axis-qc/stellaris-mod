# TODO


## bio_ship（生物舰船组）兼容衍生问题（2026-08-25 排查发现）

- [ ] A. 星舰科技第一层门槛对齐：`tech_br_arkship_construction` 前置为 `OR(tech_cruisers, tech_harbingers)`（巡洋级），比原版方舟舰 `OR(tech_destroyers, tech_weavers)`（驱逐级）高一档。普通玩家需研究到巡洋才能解锁星舰工程学；bio 玩家需研究到 tech_harbingers。是否对齐原版门槛待定。
  - 文件：`common/technology/br_arkship_spinal_tech.txt` L21-26

- [ ] B. 探索奖励事件 bio 兼容：`events/reward_exploration_events.txt` 用 `has_technology = tech_titans/battleships/cruisers/destroyers` 做船型门控，bio 玩家这些科技永远 false → 泰坦/战列/巡洋/驱逐选项被 factor=0 排除，奖励船型锁死护卫级；且 `random_owned_design = { is_ship_size = battleship }` 对 bio 玩家找不到设计。需给 bio 玩家配 OR 生物科技替代（tech_weavers/harbingers/stingers）。
  - 文件：`events/reward_exploration_events.txt` L177-232

- [ ] C. 大逃杀/PVE 初始化 `give_technology = tech_corvettes` 对 bio 无效：`events/br_level_events.txt` L29-32，bio 玩家 potential 不满足，科技给了也不产生效果。bio 玩家靠生物舰船科技链造舰，影响小，是否处理待定。
  - 文件：`events/br_level_events.txt` L29-32
