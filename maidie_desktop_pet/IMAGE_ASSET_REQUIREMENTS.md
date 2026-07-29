# Maidie 毛绒娃娃动画资源需求

## 范围

本次仅更换 Maidie 的默认精灵美术和对应外置交互动画，不修改 Agent、DeepSeek 接入、聊天、记忆、SQLite、状态机、定时/随机交流、鼠标交互、拖拽/行走/点击逻辑、对话气泡、设置、托盘、窗口透明、桌宠尺寸、缩放、碰撞、目录、打包、日志、测试、快捷键、提示词或人物性格。

## 当前项目实际格式

- 默认加载器：`animation/atlas.py`
- 默认图集：`assets/spritesheet.webp`
- 图集格式：无损 RGBA WebP
- 图集尺寸：1536×1872
- 单元格：192×208
- 网格：8 列 × 9 行
- 角色脚底基线：主图集普通落地帧为单格 `y=202`；外置动作通常为 `y=203`
- 透明背景：必须；若生图软件不支持 Alpha，可先用完全均匀的 `#00FF00` 色键背景
- 左向运行：当前 `ui/sprite.py` 在最终渲染边界镜像 row 1；本次不修改该逻辑

## 主图集状态

| 物理行 | 生成文件 | 帧数 | 整条尺寸 | 运行映射与 FPS | 循环 | 基线/动作 |
|---:|---|---:|---|---|---|---|
| 0 idle | `output/idle.png` | 6 | 1152×208 | idle 5.263 FPS；sleeping 2.381 FPS | 是 | y=202，呼吸与眨眼 |
| 1 running-right | `output/running_right.png` | 8 | 1536×208 | walk 5.405 FPS；run 10.526 FPS | 是 | y=202，朝屏幕右侧交替小步 |
| 2 running-left | `output/running_left.png` | 8 | 1536×208 | 兼容参考 5.405 FPS；当前运行时未直接读取 | 是 | y=202，单独绘制左向，禁止整条镜像 |
| 3 waving | `output/waving.png` | 4 | 768×208 | talking/reacting 5.556 FPS | 是 | y=202，轻柔挥手 |
| 4 jumping | `output/jumping.png` | 5 | 960×208 | happy 7.407 FPS | 是 | 脚底约 202/178/151/178/202 |
| 5 failed | `output/failed.png` | 8 | 1536×208 | 4.762 FPS | 是 | y=202，可爱低落/失败 |
| 6 waiting | `output/waiting.png` | 6 | 1152×208 | 5.000 FPS | 是 | y=202，等待确认 |
| 7 running | `output/running.png` | 6 | 1152×208 | thinking 5.882 FPS | 是 | y=202，任务处理/思考，不是脚步跑动 |
| 8 review | `output/review.png` | 6 | 1152×208 | 5.263 FPS | 是 | y=202，专注审阅 |

## 外置交互动作

这些资源由 `assets/actions/actions.json` 实际加载，全部为 6 帧、1152×208、单次播放：

| 状态 | 原始/目标资源 | 生成文件 | 间隔 | FPS | 动作持续配置 | 基线 |
|---|---|---|---:|---:|---:|---:|
| headpat | `assets/actions/headpat.webp` | `output/headpat.png` | 150 ms | 6.667 | 1100 ms | y=203 |
| facepoke | `assets/actions/facepoke.webp` | `output/facepoke.png` | 155 ms | 6.452 | 1100 ms | y=203 |
| shy | `assets/actions/shy.webp` | `output/shy.png` | 175 ms | 5.714 | 3000 ms | y=203 |
| celebrate | `assets/actions/celebrate.webp` | `output/celebrate.png` | 140 ms | 7.143 | 3000 ms | y=203 |
| sleepy | `assets/actions/sleepy.webp` | `output/sleepy.png` | 240 ms | 4.167 | 1600 ms | y=203 |
| dizzy-right | `assets/actions/dizzy-right.webp` | `output/dizzy_right.png` | 155 ms | 6.452 | 1100 ms | y=203 |

## 角色统一要求

所有状态必须是同一个参考图中的毛绒娃娃：

- 大头小身体，头部约占全高 55%～60%，身体和四肢短圆。
- 黑色蓬松凌乱短发、厚实分块刘海、圆润后脑勺；禁止长发、帽子和贴头发型。
- 浅色毛绒脸、紫黑渐变刺绣大眼和高光、粗黑眉、少量红色眼尾刺绣线、小红嘴、圆润小耳朵。
- 浅蓝白细条纹短袖衬衫、米白麻花针织背心、深蓝垂落小领带、浅蓝布料短裤。
- 观众视角左胸保留小狗徽章，短裤一侧保留白布标；左右动作不得出现反向文字或标签乱跳。
- 必须呈现毛绒、针织、布料和刺绣质感，禁止塑料手办、真人、写实皮肤或普通二维赛璐璐风格。

## 透明与画布

- 每帧只包含一个完整角色，四周保留安全透明边距。
- 头发、耳朵、手和脚不得裁切。
- 非跳跃帧的脚底基线不得漂移。
- 禁止白边、灰底、棋盘格、地面、投影、光晕、文字、水印、边框、帧号和网格。
- 色键方案必须是完全均匀的纯 `#00FF00`，角色内部不得使用接近该颜色的高饱和绿色。

## 提示词位置

所有完整正向提示词、动作说明、表情说明、负向提示词、方向要求和输出规格位于：

`assets_generation/prompts/`

机器可读数据位于：

`assets_generation/specifications.json`

## 生成后的替换步骤

1. 将 15 个生成结果按 `assets_generation/README.md` 指定文件名放进 `assets_generation/output/`。
2. 对色键图执行去背与边缘去绿，验证透明角、轮廓和内部 Alpha。
3. 按 192×208 单格切帧；检查帧数、角色完整性、身份一致性、基线和循环。
4. 将 9 条主动画组装为 1536×1872 的 `assets/spritesheet.webp`。
5. 将 6 条交互动画分别转换为 1152×208 的无损 RGBA WebP，替换 `assets/actions/` 中同名文件。
6. 保留 `animation/atlas.py`、`ui/sprite.py`、`assets/actions/actions.json` 的状态映射与时序不变。
7. 启动项目测试默认皮肤加载、所有状态、方向、拖拽后晕乎、摸头、戳脸、对话、思考、睡眠、点击区域和 Windows 打包路径。

## 当前未要求生成的旧文件

`assets/maidie.png`、`assets/maidie_*.gif` 与 `assets/actions/*.gif` 未被当前精灵加载器引用，因此不在这套提示词的生成范围内，也不应为了换皮而修改加载器。
