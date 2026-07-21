#!/usr/bin/env python3
"""
Sky Export Tool GUI - 光遇地图导出工具 可视化界面
"""

import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import sys
import os
import re
import threading
import queue
import json
import subprocess
from collections import OrderedDict

_ANSI_RE = re.compile(r"\033\[[0-9;]*m")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SCRIPT_DIR)

SCENE_ORDER = ["dawn", "prairie", "rain", "sunset", "dusk", "night", "storm"]
SCENE_DISPLAY = {
    "dawn": "晨岛", "prairie": "云野", "rain": "雨林",
    "sunset": "霞谷", "dusk": "墓土", "night": "禁阁", "storm": "伊甸",
}


class StdoutRedirector:
    def __init__(self, q):
        self.q = q

    def write(self, s):
        if s:
            self.q.put(_ANSI_RE.sub("", s))

    def flush(self):
        pass


class SkyExportGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Sky Export Tool")
        self.root.geometry("1060x740")
        self.root.minsize(900, 620)

        self.running = False
        self.log_queue = queue.Queue()
        self.marker_vars = {}
        self.map_entries = OrderedDict()
        self.scene_vars = {}

        self._modules_loaded = False
        self._export_map_fn = None
        self._export_single_map_fn = None
        self._bintojson_path = os.path.join(SCRIPT_DIR, "bintojson.py")

        self._setup_style()
        self._build_ui()
        self._poll_log()
        self._import_modules()

    def _setup_style(self):
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("Title.TLabel", font=("Segoe UI", 16, "bold"))
        style.configure("Sub.TLabel", font=("Segoe UI", 9), foreground="#666")
        style.configure("H.TLabel", font=("Segoe UI", 9, "bold"))
        style.configure(
            "Run.TButton", font=("Segoe UI", 10, "bold"), padding=(16, 6)
        )
        style.configure("Scene.TCheckbutton", font=("Segoe UI", 9, "bold"))

    def _build_ui(self):
        # header
        hdr = ttk.Frame(self.root, padding=(16, 10, 16, 4))
        hdr.pack(fill="x")
        ttk.Label(hdr, text="Sky Export Tool", style="Title.TLabel").pack(
            side="left"
        )
        ttk.Label(
            hdr, text="光遇地图导出工具  v18", style="Sub.TLabel"
        ).pack(side="left", padx=(10, 0), pady=(6, 0))

        # game directory row
        dir_frame = ttk.Frame(self.root, padding=(16, 4, 16, 0))
        dir_frame.pack(fill="x")
        dir_frame.columnconfigure(1, weight=1)
        ttk.Label(dir_frame, text="游戏目录:", style="H.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        self.game_dir_var = tk.StringVar()
        ttk.Entry(dir_frame, textvariable=self.game_dir_var).grid(
            row=0, column=1, sticky="ew", padx=(6, 4)
        )
        ttk.Button(
            dir_frame, text="浏览", width=6, command=self._browse_game_dir
        ).grid(row=0, column=2)
        ttk.Button(
            dir_frame, text="扫描", width=6, command=self._scan_game_dir
        ).grid(row=0, column=3, padx=(4, 0))
        ttk.Label(
            self.root,
            text='选择游戏安装根目录 (如 "Sky Children of the Light")，点击「扫描」自动识别地图和 Mesh',
            foreground="#888",
            font=("Segoe UI", 8),
        ).pack(anchor="w", padx=(18, 0))

        # mid section: left (maps) + right (options + markers)
        mid_frame = ttk.Frame(self.root)
        mid_frame.pack(fill="both", expand=True, padx=16, pady=(6, 0))

        # ── left: map list ──
        map_frame = ttk.LabelFrame(
            mid_frame, text="地图列表", padding=(8, 4, 8, 6)
        )
        map_frame.pack(side="left", fill="both", expand=True)

        map_toolbar = ttk.Frame(map_frame)
        map_toolbar.pack(fill="x", pady=(0, 4))
        ttk.Button(
            map_toolbar, text="全选", width=5, command=self._select_all_maps
        ).pack(side="left")
        ttk.Button(
            map_toolbar,
            text="全不选",
            width=5,
            command=self._deselect_all_maps,
        ).pack(side="left", padx=(4, 0))
        self.map_count_label = ttk.Label(
            map_toolbar, text="", foreground="#666", font=("Segoe UI", 8)
        )
        self.map_count_label.pack(side="right")

        self.map_canvas = tk.Canvas(map_frame, highlightthickness=0)
        map_scroll = ttk.Scrollbar(
            map_frame, orient="vertical", command=self.map_canvas.yview
        )
        self.map_inner = ttk.Frame(self.map_canvas)
        self.map_inner.bind(
            "<Configure>",
            lambda e: self.map_canvas.configure(
                scrollregion=self.map_canvas.bbox("all")
            ),
        )
        self.map_canvas.create_window(
            (0, 0), window=self.map_inner, anchor="nw"
        )
        self.map_canvas.configure(yscrollcommand=map_scroll.set)
        self.map_canvas.pack(side="left", fill="both", expand=True)
        map_scroll.pack(side="right", fill="y")
        self._bind_mousewheel(self.map_canvas)

        ttk.Label(
            self.map_inner,
            text='指定游戏目录后点击「扫描」',
            foreground="#999",
        ).pack(anchor="w", padx=4, pady=2)

        # ── right panel ──
        right_panel = ttk.Frame(mid_frame)
        right_panel.pack(
            side="right", fill="both", expand=True, padx=(8, 0)
        )

        # options
        opt_frame = ttk.LabelFrame(
            right_panel, text="选项", padding=(12, 6, 12, 8)
        )
        opt_frame.pack(fill="x")

        row0 = ttk.Frame(opt_frame)
        row0.pack(fill="x")
        row0.columnconfigure(1, weight=1)
        ttk.Label(row0, text="Mesh 文件夹:", style="H.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        self.mesh_var = tk.StringVar()
        ttk.Entry(row0, textvariable=self.mesh_var).grid(
            row=0, column=1, sticky="ew", padx=(6, 4)
        )
        ttk.Button(
            row0, text="浏览", width=6, command=self._browse_mesh
        ).grid(row=0, column=2)
        ttk.Label(
            opt_frame,
            text="扫描后自动填充 | 也可手动指定 .mesh 文件所在目录",
            foreground="#888",
            font=("Segoe UI", 8),
        ).pack(anchor="w", padx=(2, 0))

        row_out = ttk.Frame(opt_frame)
        row_out.pack(fill="x", pady=(4, 0))
        row_out.columnconfigure(1, weight=1)
        ttk.Label(row_out, text="输出目录:", style="H.TLabel").grid(
            row=0, column=0, sticky="w"
        )
        self.output_var = tk.StringVar()
        ttk.Entry(row_out, textvariable=self.output_var).grid(
            row=0, column=1, sticky="ew", padx=(6, 4)
        )
        ttk.Button(
            row_out, text="浏览", width=6, command=self._browse_output
        ).grid(row=0, column=2)
        ttk.Label(
            opt_frame,
            text="留空则默认输出到游戏目录下的 Export_Output",
            foreground="#888",
            font=("Segoe UI", 8),
        ).pack(anchor="w", padx=(2, 0))

        self.marker_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(
            opt_frame,
            text="导出标记小球",
            variable=self.marker_var,
            command=self._on_marker_toggle,
        ).pack(anchor="w", pady=(6, 0))

        # marker classes
        marker_frame = ttk.LabelFrame(
            right_panel, text="标记类名", padding=(8, 4, 8, 6)
        )
        marker_frame.pack(fill="both", expand=True, pady=(6, 0))

        mk_toolbar = ttk.Frame(marker_frame)
        mk_toolbar.pack(fill="x", pady=(0, 4))
        self.scan_mk_btn = ttk.Button(
            mk_toolbar, text="扫描", command=self._scan_markers
        )
        self.scan_mk_btn.pack(side="left")
        self.sel_all_mk_btn = ttk.Button(
            mk_toolbar,
            text="全选",
            width=5,
            command=self._select_all_markers,
        )
        self.sel_all_mk_btn.pack(side="left", padx=(6, 0))
        self.desel_all_mk_btn = ttk.Button(
            mk_toolbar,
            text="全不选",
            width=5,
            command=self._deselect_all_markers,
        )
        self.desel_all_mk_btn.pack(side="left", padx=(4, 0))

        self.marker_canvas = tk.Canvas(marker_frame, highlightthickness=0)
        marker_scroll = ttk.Scrollbar(
            marker_frame,
            orient="vertical",
            command=self.marker_canvas.yview,
        )
        self.marker_inner = ttk.Frame(self.marker_canvas)
        self.marker_inner.bind(
            "<Configure>",
            lambda e: self.marker_canvas.configure(
                scrollregion=self.marker_canvas.bbox("all")
            ),
        )
        self.marker_canvas.create_window(
            (0, 0), window=self.marker_inner, anchor="nw"
        )
        self.marker_canvas.configure(yscrollcommand=marker_scroll.set)
        self.marker_canvas.pack(side="left", fill="both", expand=True)
        marker_scroll.pack(side="right", fill="y")
        self._bind_mousewheel(self.marker_canvas)

        ttk.Label(
            self.marker_inner,
            text='点击「扫描」加载可选类名',
            foreground="#999",
        ).pack(anchor="w", padx=4, pady=2)

        # buttons
        btn_frame = ttk.Frame(self.root, padding=(16, 8, 16, 0))
        btn_frame.pack(fill="x")
        self.run_btn = ttk.Button(
            btn_frame,
            text="开始导出",
            style="Run.TButton",
            command=self._start_export,
        )
        self.run_btn.pack(side="left")
        self.stop_btn = ttk.Button(
            btn_frame,
            text="中止",
            command=self._stop_export,
            state="disabled",
        )
        self.stop_btn.pack(side="left", padx=(8, 0))
        ttk.Button(
            btn_frame, text="清空日志", command=self._clear_log
        ).pack(side="right")
        ttk.Button(
            btn_frame, text="打开输出目录", command=self._open_output
        ).pack(side="right", padx=(0, 8))

        # progress
        self.progress = ttk.Progressbar(self.root, mode="indeterminate")
        self.progress.pack(fill="x", padx=16, pady=(6, 0))

        # log output
        log_frame = ttk.LabelFrame(
            self.root, text="日志输出", padding=(4, 2, 4, 4)
        )
        log_frame.pack(fill="both", expand=True, padx=16, pady=(6, 12))
        self.log_text = tk.Text(
            log_frame,
            wrap="word",
            font=("Consolas", 9),
            bg="#1e1e1e",
            fg="#dcdcdc",
            insertbackground="#dcdcdc",
            state="disabled",
            relief="flat",
            height=8,
        )
        log_scroll = ttk.Scrollbar(
            log_frame, orient="vertical", command=self.log_text.yview
        )
        self.log_text.configure(yscrollcommand=log_scroll.set)
        self.log_text.pack(side="left", fill="both", expand=True)
        log_scroll.pack(side="right", fill="y")

        self.log_text.tag_configure("ok", foreground="#6ec86e")
        self.log_text.tag_configure("warn", foreground="#e0c040")
        self.log_text.tag_configure("err", foreground="#e05050")
        self.log_text.tag_configure("info", foreground="#60a0d0")

        self._last_output_dir = None

    # ── mousewheel ─────────────────────────────────────────
    def _bind_mousewheel(self, canvas):
        def _on_enter(e):
            canvas.bind_all(
                "<MouseWheel>",
                lambda ev: canvas.yview_scroll(-ev.delta // 120, "units"),
            )

        def _on_leave(e):
            canvas.unbind_all("<MouseWheel>")

        canvas.bind("<Enter>", _on_enter)
        canvas.bind("<Leave>", _on_leave)

    # ── browse ─────────────────────────────────────────────
    def _browse_game_dir(self):
        p = filedialog.askdirectory(title="选择光遇游戏安装目录")
        if p:
            self.game_dir_var.set(p)
            self._scan_game_dir()

    def _browse_mesh(self):
        p = filedialog.askdirectory(title="选择 Mesh 文件夹")
        if p:
            self.mesh_var.set(p)

    def _browse_output(self):
        p = filedialog.askdirectory(title="选择输出目录")
        if p:
            self.output_var.set(p)

    # ── game dir scanning ──────────────────────────────────
    def _scan_game_dir(self):
        game_dir = self.game_dir_var.get().strip()
        if not game_dir or not os.path.isdir(game_dir):
            messagebox.showwarning("提示", "请先选择有效的游戏目录")
            return

        assets_dir = os.path.join(game_dir, "data", "assets")
        if not os.path.isdir(assets_dir):
            messagebox.showwarning(
                "提示",
                "未找到 data/assets 目录\n请确认选择了正确的游戏安装根目录",
            )
            return

        # auto-detect mesh dir
        mesh_dir = os.path.join(assets_dir, "meshes", "Data", "Meshes", "Bin")
        if os.path.isdir(mesh_dir):
            self.mesh_var.set(mesh_dir)
            mesh_count = sum(
                1 for f in os.listdir(mesh_dir) if f.endswith(".mesh")
            )
            self._log(f"[OK] Mesh 目录: {mesh_count} 个 .mesh 文件\n")

        # scan scenes
        try:
            entries = set(os.listdir(assets_dir))
        except OSError as e:
            messagebox.showerror("错误", str(e))
            return

        scene_list = [s for s in SCENE_ORDER if s in entries]
        for entry in sorted(entries):
            if entry not in SCENE_ORDER and entry != "meshes":
                levels = os.path.join(assets_dir, entry, "Data", "Levels")
                if os.path.isdir(levels):
                    scene_list.append(entry)

        self.map_entries.clear()
        self.scene_vars.clear()
        total_maps = 0

        for scene in scene_list:
            levels_dir = os.path.join(assets_dir, scene, "Data", "Levels")
            if not os.path.isdir(levels_dir):
                continue
            maps = []
            try:
                for entry in sorted(os.listdir(levels_dir)):
                    sub = os.path.join(levels_dir, entry)
                    if os.path.isdir(sub) and os.path.exists(
                        os.path.join(sub, "Objects.level.bin")
                    ):
                        maps.append((entry, sub, tk.BooleanVar(value=True)))
            except OSError:
                continue
            if maps:
                self.scene_vars[scene] = tk.BooleanVar(value=True)
                self.map_entries[scene] = maps
                total_maps += len(maps)

        self._populate_map_list()
        self._log(
            f"[OK] 扫描完成: {len(self.map_entries)} 个区域, {total_maps} 张地图\n"
        )

    def _populate_map_list(self):
        for w in self.map_inner.winfo_children():
            w.destroy()

        if not self.map_entries:
            ttk.Label(
                self.map_inner, text="未找到地图", foreground="#999"
            ).pack(anchor="w", padx=4)
            self._update_map_count()
            return

        for scene, maps in self.map_entries.items():
            display = SCENE_DISPLAY.get(scene, scene)
            scene_var = self.scene_vars[scene]

            ttk.Checkbutton(
                self.map_inner,
                text=f"{display} ({scene}) — {len(maps)} 张",
                variable=scene_var,
                style="Scene.TCheckbutton",
                command=lambda s=scene: self._toggle_scene(s),
            ).pack(anchor="w", padx=2, pady=(6, 1))

            for name, path, var in maps:
                ttk.Checkbutton(
                    self.map_inner, text=name, variable=var
                ).pack(anchor="w", padx=(24, 4), pady=0)

        self._update_map_count()

    def _toggle_scene(self, scene):
        val = self.scene_vars[scene].get()
        for _, _, var in self.map_entries[scene]:
            var.set(val)
        self._update_map_count()

    def _select_all_maps(self):
        for sv in self.scene_vars.values():
            sv.set(True)
        for maps in self.map_entries.values():
            for _, _, var in maps:
                var.set(True)
        self._update_map_count()

    def _deselect_all_maps(self):
        for sv in self.scene_vars.values():
            sv.set(False)
        for maps in self.map_entries.values():
            for _, _, var in maps:
                var.set(False)
        self._update_map_count()

    def _update_map_count(self):
        total = sum(len(m) for m in self.map_entries.values())
        selected = sum(
            1
            for maps in self.map_entries.values()
            for _, _, v in maps
            if v.get()
        )
        self.map_count_label.configure(text=f"已选 {selected}/{total}")

    def _get_selected_maps(self):
        result = []
        for maps in self.map_entries.values():
            for name, path, var in maps:
                if var.get():
                    result.append((name, path))
        return result

    # ── marker scanning ───────────────────────────────────
    def _on_marker_toggle(self):
        state = "normal" if self.marker_var.get() else "disabled"
        self.scan_mk_btn.configure(state=state)
        self.sel_all_mk_btn.configure(state=state)
        self.desel_all_mk_btn.configure(state=state)

    def _scan_markers(self):
        selected = self._get_selected_maps()
        if not selected:
            messagebox.showwarning("提示", "请先扫描游戏目录并选择至少一张地图")
            return

        self._log("正在扫描标记类名...\n")
        classes = set()
        for name, path in selected:
            bin_file = os.path.join(path, "Objects.level.bin")
            if not os.path.exists(bin_file):
                for f in os.listdir(path):
                    if f.endswith(".bin") and not f.endswith(".meshes"):
                        bin_file = os.path.join(path, f)
                        break

            if not os.path.exists(bin_file):
                continue

            json_path = bin_file + ".json"
            if not os.path.exists(json_path) and os.path.exists(
                self._bintojson_path
            ):
                subprocess.run(
                    [sys.executable, self._bintojson_path, bin_file],
                    capture_output=True,
                    cwd=path,
                )

            if not os.path.exists(json_path):
                continue

            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                bst = data.get("BSTNodes", {})
                for nd in bst.values():
                    if isinstance(nd, dict):
                        for cn in nd:
                            if "LevelMesh" not in cn:
                                classes.add(cn)
            except Exception:
                pass

        self._populate_marker_checkboxes(sorted(classes))
        self._log(f"扫描完成: 找到 {len(classes)} 个标记类名\n")

    def _populate_marker_checkboxes(self, class_names):
        for w in self.marker_inner.winfo_children():
            w.destroy()
        self.marker_vars.clear()

        if not class_names:
            ttk.Label(
                self.marker_inner,
                text="未找到标记类名",
                foreground="#999",
            ).pack(anchor="w", padx=4)
            return

        cols = 2
        for i, cn in enumerate(class_names):
            var = tk.BooleanVar(value=True)
            self.marker_vars[cn] = var
            r, c = divmod(i, cols)
            display = cn if len(cn) <= 32 else cn[:29] + "..."
            ttk.Checkbutton(
                self.marker_inner, text=display, variable=var
            ).grid(row=r, column=c, sticky="w", padx=(4, 12), pady=1)

    def _select_all_markers(self):
        for v in self.marker_vars.values():
            v.set(True)

    def _deselect_all_markers(self):
        for v in self.marker_vars.values():
            v.set(False)

    # ── module import ──────────────────────────────────────
    def _import_modules(self):
        try:
            import importlib.util
            import io as _io

            launcher_path = os.path.join(SCRIPT_DIR, "启动.py")
            if os.path.exists(launcher_path):
                old_out, old_err = sys.stdout, sys.stderr
                sys.stdout = _io.StringIO()
                sys.stderr = _io.StringIO()
                try:
                    spec = importlib.util.spec_from_file_location(
                        "_launcher", launcher_path
                    )
                    mod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(mod)
                    self._export_map_fn = getattr(mod, "export_map", None)
                finally:
                    sys.stdout, sys.stderr = old_out, old_err

            batch_path = os.path.join(SCRIPT_DIR, "批量地图转换.py")
            if os.path.exists(batch_path):
                old_out, old_err = sys.stdout, sys.stderr
                sys.stdout = _io.StringIO()
                sys.stderr = _io.StringIO()
                try:
                    spec = importlib.util.spec_from_file_location(
                        "_batch", batch_path
                    )
                    bmod = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(bmod)
                    self._export_single_map_fn = getattr(
                        bmod, "export_single_map", None
                    )
                finally:
                    sys.stdout, sys.stderr = old_out, old_err

            self._modules_loaded = True
            self._log("[OK] 模块加载完成\n")
        except Exception as e:
            self._log(f"[WARN] 模块加载失败: {e}\n")

    # ── export ─────────────────────────────────────────────
    def _start_export(self):
        if self.running:
            return

        selected = self._get_selected_maps()
        if not selected:
            messagebox.showwarning("提示", "请选择至少一张地图")
            return

        mesh_dir = self.mesh_var.get().strip()
        output_dir = self.output_var.get().strip() or None
        export_markers = self.marker_var.get()

        enabled_classes = None
        if export_markers and self.marker_vars:
            enabled_classes = [
                cn for cn, v in self.marker_vars.items() if v.get()
            ]

        self.running = True
        self.run_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")
        self.progress.start(15)

        t = threading.Thread(
            target=self._do_export,
            args=(selected, mesh_dir, export_markers, enabled_classes, output_dir),
            daemon=True,
        )
        t.start()

    def _do_export(
        self, selected, mesh_dir, export_markers, enabled_classes, output_dir
    ):
        redirector = StdoutRedirector(self.log_queue)
        old_out, old_err = sys.stdout, sys.stderr
        sys.stdout = redirector
        sys.stderr = redirector
        try:
            if len(selected) == 1 and self._export_map_fn:
                name, path = selected[0]
                self.log_queue.put(f"导出地图: {name}\n\n")
                result = self._export_map_fn(
                    path,
                    mesh_dir,
                    export_markers,
                    enabled_classes,
                    output_dir=output_dir,
                )
                if result:
                    self._last_output_dir = result
            elif self._export_single_map_fn:
                if not output_dir:
                    game_dir = self.game_dir_var.get().strip()
                    if game_dir:
                        output_dir = os.path.join(game_dir, "Export_Output")
                    else:
                        output_dir = os.path.join(
                            os.path.dirname(selected[0][1]), "输出"
                        )
                os.makedirs(output_dir, exist_ok=True)
                self._last_output_dir = output_dir

                total = len(selected)
                self.log_queue.put(f"开始导出 {total} 张地图\n\n")
                success = 0
                fail = 0

                for i, (name, path) in enumerate(selected, 1):
                    if not self.running:
                        self.log_queue.put("\n⚠️ 已中止\n")
                        break
                    self.log_queue.put(f"[{i}/{total}] {name}\n")
                    log_entry = {}
                    ok = self._export_single_map_fn(
                        path,
                        mesh_dir,
                        output_dir,
                        export_markers,
                        enabled_classes,
                        log_entry,
                    )
                    if ok:
                        success += 1
                        tv = log_entry.get("terrain_verts", 0)
                        tt = log_entry.get("terrain_tris", 0)
                        mc = log_entry.get("models_count", 0)
                        mi = log_entry.get("models_instances", 0)
                        mk = log_entry.get("markers_count", 0)
                        self.log_queue.put(
                            f"   ✅ 地形:{tv}v/{tt}t  模型:{mc}种/{mi}实例  标记:{mk}\n"
                        )
                    else:
                        fail += 1
                        err = log_entry.get("error", "未知")
                        self.log_queue.put(f"   ❌ {err}\n")

                self.log_queue.put(
                    f"\n批量导出完成: 成功 {success}/{total}，失败 {fail}\n"
                )
            else:
                self.log_queue.put("❌ 导出模块未加载\n")
        except Exception as e:
            self.log_queue.put(f"\n❌ 导出出错: {e}\n")
        finally:
            sys.stdout, sys.stderr = old_out, old_err
            self.root.after(0, self._export_done)

    def _export_done(self):
        self.running = False
        self.run_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")
        self.progress.stop()
        self.root.bell()

    def _stop_export(self):
        self.running = False
        self._log("正在中止...\n")

    # ── log ────────────────────────────────────────────────
    def _log(self, msg):
        self.log_queue.put(msg)

    def _poll_log(self):
        batch = []
        try:
            while True:
                batch.append(self.log_queue.get_nowait())
        except queue.Empty:
            pass

        if batch:
            self.log_text.configure(state="normal")
            for msg in batch:
                tag = None
                if "✅" in msg or "[OK]" in msg:
                    tag = "ok"
                elif "❌" in msg or "[ERR]" in msg:
                    tag = "err"
                elif "⚠️" in msg or "[WARN]" in msg:
                    tag = "warn"
                elif "📖" in msg or "📝" in msg or "🔍" in msg:
                    tag = "info"
                if tag:
                    self.log_text.insert(tk.END, msg, (tag,))
                else:
                    self.log_text.insert(tk.END, msg)
            self.log_text.see(tk.END)
            self.log_text.configure(state="disabled")

        self.root.after(80, self._poll_log)

    def _clear_log(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", tk.END)
        self.log_text.configure(state="disabled")

    def _open_output(self):
        if self._last_output_dir and os.path.isdir(self._last_output_dir):
            os.startfile(self._last_output_dir)
            return
        out = self.output_var.get().strip()
        if out and os.path.isdir(out):
            os.startfile(out)
            return
        messagebox.showinfo("提示", "没有可打开的输出目录")


def main():
    root = tk.Tk()
    try:
        root.iconbitmap(default="")
    except tk.TclError:
        pass
    SkyExportGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
