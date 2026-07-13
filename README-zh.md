# Sky-map-to-obj

从《光·遇》游戏地图中导出地形、场景模型和交互标记为 OBJ 文件。

[中文](./README-zh.md) | [English](./README.md)

## 功能

解析游戏二进制地图数据，输出标准 `.obj` 文件，可直接导入 Blender、UE5 等 3D 软件。

| 数据 | 源格式 | 输出 |
|------|--------|------|
| 地形网格 | `BstBaked.meshes` (LZ4 + meshopt) | 顶点 + 法线，按材质着色的顶点颜色 |
| 场景模型 | `.mesh` (v23–v32) | 已应用 Transform 的实例 |
| 交互标记 | `Objects.level.bin` | 传送门、NPC、冥想区等位置的彩色小球 |

支持 `.meshes` 版本 v55–v57+ (LVL04–LVL0D)。

## 文件结构

```
tool/文件/
├── 启动.py              # ⭐ 单地图导出（交互式，推荐）
├── 批量地图转换.py       # 批量导出目录下所有地图
├── Sky_Bstbake.py       # 核心地形解析引擎（BstBaked.meshes → 顶点/索引）
├── meshtoobj.py         # .mesh 模型解析器（v23–v32）
├── bintojson.py         # .bin ↔ .json 双向转换器
├── 单独启动Sky_Bstbake.py  # 独立地形导出
├── _meshopt/
│   └── meshopt2.dll     # meshopt 解码库（Windows，ctypes 回退）
└── 环境.txt             # 依赖安装说明
```

## 依赖

Python 3.8+

```bash
pip install lz4 meshoptimizer
```

<details>
<summary>Termux (Android)</summary>

```bash
pkg update && pkg upgrade
pkg install python clang cmake make binutils git
pip install lz4 meshoptimizer
```
</details>

## 使用方法

### 单地图导出

```bash
cd tool/文件
python 启动.py
```

按提示输入：
1. 地图文件夹路径（包含 `Objects.level.bin` 和 `BstBaked.meshes` 的目录）
2. mesh 文件夹路径（存放已提取的 `.mesh` 文件）
3. 是否导出标记小球 (y/n)

输出：`<地图文件夹>/<地图名>_export/<地图名>.obj`

### 批量导出

```bash
python 批量地图转换.py
```

按提示输入：
1. Level 目录路径（包含所有地图子文件夹的上级目录）
2. mesh 文件夹路径
3. 是否导出标记小球 (y/n)

输出：`<Level 目录>/../输出/<地图名>/<地图名>.obj`

### 仅导出地形

```bash
python 单独启动Sky_Bstbake.py
```

或直接调用核心脚本：

```bash
python Sky_Bstbake.py --unpack BstBaked.meshes --export-obj
```

### .bin 与 .json 互转

```bash
python bintojson.py Objects.level.bin    # → .json
python bintojson.py Objects.level.json   # → .bin
```

## OBJ 输出内容

导出的 OBJ 最多包含三个部分：

- **地形** — 地面网格，带法线和按材质着色的顶点颜色
- **模型实例** — 场景物体（石头、建筑、植物等），已应用变换矩阵，Z 轴翻转适配 Blender
- **标记小球**（可选）— 交互点位置的彩色球体：

| 类名 | 颜色 |
|------|------|
| Marker | 金色 |
| Npc | 绿色 |
| MeditationArea | 蓝色 |
| Portal | 红色 |
| Checkpoint | 橙色 |
| Wind | 天蓝 |
| Water | 深蓝 |
| Flame | 橙红 |
| PointLight | 暖黄 |
| SoundEmitter | 青色 |
| Timeline | 紫色 |

## 常见问题

| 问题 | 解决 |
|------|------|
| 缺少 `lz4` | `pip install lz4` |
| 缺少 `meshoptimizer` | `pip install meshoptimizer`（Termux 需先装 clang/cmake） |
| 地形 0 顶点 | meshopt 解码失败 — 检查 meshoptimizer 安装，Windows 上将 `meshopt2.dll` 放入 `_meshopt/` |
| 模型缺失 | 需另行从游戏资源包中提取 `.mesh` 文件 |

## 致谢

基于以下项目：
- checion (雨人) & Heriel (落秋) — [SkyBstbake](https://github.com/ThatSkyOldServer/SkyBstbake)
- Miau — [Sky-.bin-reader](https://github.com/Miau0x1/Sky-.bin-reader)
- potato — 脚本
- 十二 — 整合封装、[Sky-.bin-reader-python-zh](https://github.com/skyIshier/Sky-.bin-reader-python-zh)

## 许可证

MIT — 见 [LICENSE](./LICENSE)。
