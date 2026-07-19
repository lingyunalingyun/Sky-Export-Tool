# Sky-Export-Tool

Export terrain, scene models, and interaction markers from *Sky: Children of the Light* maps to OBJ.

[中文](./README-zh.md) | [English](./README.md)

## What it does

Parses the game's binary map data and outputs standard `.obj` files you can open in Blender, UE5, or any 3D software.

| Data | Source format | Output |
|------|--------------|--------|
| Terrain mesh | `BstBaked.meshes` (LZ4 + meshopt) | Vertices + normals, per-material vertex colors |
| Scene models | `.mesh` (v23–v32) | Positioned instances with transforms applied |
| Interaction markers | `Objects.level.bin` | Colored spheres for portals, NPCs, meditation spots, etc. |

Supports `.meshes` versions v55–v57+ (LVL04–LVL0D).

## File structure

```
tool/文件/
├── 启动.py              # Single map export (interactive, recommended)
├── 批量地图转换.py       # Batch export all maps in a directory
├── Sky_Bstbake.py       # Core terrain parser (BstBaked.meshes → vertices/indices)
├── sky_mesh_to_obj.py   # .mesh model parser v2 (v31/v32, ZipPos/ZipUvs/LZ4)
├── meshtoobj.py         # .mesh model parser legacy (v23–v30)
├── bintojson.py         # .bin ↔ .json converter (Objects.level.bin)
├── 单独启动Sky_Bstbake.py  # Standalone terrain-only export
├── _meshopt/
│   └── meshopt2.dll     # meshopt decoder (Windows, ctypes fallback)
└── 环境.txt             # Dependency install notes
```

## Requirements

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

## Usage

### Single map export

```bash
cd tool/文件
python 启动.py
```

Prompts:
1. Map folder path (the directory containing `Objects.level.bin` and `BstBaked.meshes`)
2. Mesh folder path (directory of extracted `.mesh` files)
3. Export marker spheres? (y/n)

Output: `<map_folder>/<map_name>_export/<map_name>.obj`

### Batch export

```bash
python 批量地图转换.py
```

Prompts:
1. Level directory (parent containing all map subdirectories)
2. Mesh folder path
3. Export marker spheres? (y/n)

Output: `<level_dir>/../输出/<map_name>/<map_name>.obj`

### Terrain only (standalone)

```bash
python 单独启动Sky_Bstbake.py
```

Or use `Sky_Bstbake.py` directly:

```bash
python Sky_Bstbake.py --unpack BstBaked.meshes --export-obj
```

### .bin ↔ .json conversion

```bash
python bintojson.py Objects.level.bin    # → .json
python bintojson.py Objects.level.json   # → .bin
```

## OBJ output contents

The exported OBJ contains up to three object groups:

- **Terrain** — ground mesh with normals and per-material vertex colors
- **Model instances** — scene objects (rocks, buildings, flora, etc.) with transforms applied, Z-axis flipped for Blender
- **Marker spheres** (optional) — colored spheres at interaction points:

| Class | Color |
|-------|-------|
| Marker | Gold |
| Npc | Green |
| MeditationArea | Blue |
| Portal | Red |
| Checkpoint | Orange |
| Wind | Sky blue |
| Water | Deep blue |
| Flame | Orange-red |
| PointLight | Warm yellow |
| SoundEmitter | Cyan |
| Timeline | Purple |

## Prompt translation reference

Since the scripts use Chinese prompts:

| Chinese | English |
|---------|---------|
| 地图文件夹 | Map folder path |
| mesh 文件夹路径 | Mesh folder path |
| 是否导出标记小球? | Export marker spheres? (y/n) |
| Level 目录路径 | Level directory path |
| 是否开始批量导出? | Start batch export? (y/n) |

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `lz4` not found | `pip install lz4` |
| `meshoptimizer` not found | `pip install meshoptimizer` (Termux: install clang/cmake first) |
| Terrain 0 vertices | meshopt decode failed — check meshoptimizer install, or place `meshopt2.dll` in `_meshopt/` on Windows |
| Models missing | Need to extract `.mesh` files from game assets separately |

## Credits

Based on work by:
- checion (雨人) & Heriel (落秋) — [SkyBstbake](https://github.com/ThatSkyOldServer/SkyBstbake)
- Miau — [Sky-.bin-reader](https://github.com/Miau0x1/Sky-.bin-reader)
- potato — scripts
- 十二 — integration, [Sky-.bin-reader-python-zh](https://github.com/skyIshier/Sky-.bin-reader-python-zh)

## License

MIT — see [LICENSE](./LICENSE).
