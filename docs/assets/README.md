# DSH Desktop 品牌封图 · 设计说明

**深色蓝图 / 工程图纸风（Dark Blueprint）** 的品牌视觉一套，共两张主图 + 一张预览页：

| 文件 | 规格 | 用途 |
|---|---|---|
| `social-preview.svg` / `social-preview.png` | 1200×630（PNG 输出 @2x=2400×1260） | GitHub 仓库社交预览图（仓库首屏缩略图） |
| `banner.svg` / `banner.png` | 1280×320（PNG 输出 @2x=2560×640） | README 顶部横幅 |
| `preview.html` | — | 浏览器离线预览页，便于放大核对 |


## 一、配色（同一调色板 · 深色蓝图模式）

沿用了 DSH 现有 UI 的品牌蓝 `#4d6bfe` 与深色底 `#101319`，并叠加 `design-specifications` 的 Dark Blueprint 色彩系统：

| Token | 值 | 用途 |
|---|---|---|
| `--bg` 背景 | `#0A1424` | 极夜暗蓝图纸底色 |
| `--bg-card` 卡片 | `#0E1B30` | 鲸鱼卡 / 面板底 |
| `--primary` 主色 | `#00F0FF` 电光青 | 总线框、标题、鲸鱼描边 |
| `--brand` 品牌蓝 | `#4D6BFE` | 标题「Desktop」、虚线衬框、鲸鱼填充 |
| `--accent` 强调橙 | `#FF5E00` | 状态印章、坐标/步骤箭头、个别高亮字 |
| `--ink` 前景文字 | `#E6F4F7` | 主标题 / 副标题主体 |
| `--muted` 次要文字 | `#6C7E99` | 技术标注、刻度、页脚 |
| 网格 | `rgba(0,240,255,0.055)` | 28px / 24px 规则网格 |

> 说明：任务要求覆盖 `#0A1424` 深蓝底与 `#101319` 品牌深底，二者相近，主图采用 `#0A1424`（更贴合蓝图）；品牌蓝仅作为 `#4d6bfe` 点缀（虚线框、鲸鱼半透明填充、标签描边）。


## 二、构图（v2 减法重设计：极简聚焦 · 强留白）

设计方向切换为**减法**：只保留核心信息与唯一图形焦点，删去全部技术性装饰（坐标/尺寸刻度/准星括号群/MOUNT・SCALE・OFFICIAL・STATUS 等标签、流水线三框、AUTO-BOOTSTRAP/3-STAGE），保证缩到 GitHub README 宽度仍清晰、不碎不乱。

### ① 社交预览图 1200×630 —— 居中英雄式
- **鲸鱼**（唯一图形焦点，240px）正中央，配一圈极淡虚线环；上空与两侧大留白。
- **主标题** `DSH Desktop`（92px，DSH 青 / Desktop 白）居中于鲸鱼下方。
- **副标题** `DeepSeek Harness 桌面版`（40px，沉稳灰），与标题留足间距。
- **三个 chip**（一键启动 / 远程访问 / 插件市场，30px；末位橙色强调）居中一行，圆角微线框。
- **一行极小编号** `[ v2.0 · WINDOWS DOT-AND-PLAY LAUNCHER ]`（16px mono）。
- 核心可见元素：鲸鱼 + 标题 + 副标题 + 3 chip + 版本行 = **7 个**；纵向节奏为 鲸鱼→标题→副标题→chips→版本，各带充足呼吸空间。

### ② README 横幅 1280×320 —— 横向极简
- **鲸鱼**（150px）居中于画布垂直中线、靠左，唯一图形焦点。
- **主标题** `DSH Desktop`（92px）+ **slogan** `一键零配置 · 远程访问 · 服务守护`（40px）+ **一行 meta**（16px：`DESKTOP LAUNCHER FOR DEEPSEEK HARNESS · v2.0 · WINDOWS`）。
- 仅一条极淡竖向分隔线衔接鲸鱼与文字区；无准星、无刻度、无坐标、无版本框。
- 核心可见元素：鲸鱼 + 标题 + slogan + meta = **4 个**，右侧留白充足。

> 两图仅保留元素间 ≥24px 呼吸间距与四周 ≥40px 安全边距；色板 / 网格（更稀疏更淡）/ 鲸鱼资产不变。


## 三、字体

全部使用**系统字体栈**，SVG 内不 `@import`、无外部字体加载，可离线渲染：

- 无衬线正文栈：`"Segoe UI","Microsoft YaHei",-apple-system,sans-serif`
- 等宽技术栈：`Consolas,"JetBrains Mono","Courier New",monospace`
- 分工：大标题 / slogan / 功能词用无衬线粗体；标签、刻度、坐标、`[SPEC]`/`[STATUS]` 用等宽字体 + 字距微扩（letter-spacing 0.05em–0.1em），强调工程感。


## 四、鲸鱼资产（品牌规范）

- 路径直接取自项目官方 `favicon.svg` 的完整 `d` 数据（未重构、未替换、未臆造），保证可辨识。
- 蓝图风风格化：`fill=rgba(77,107,254,0.30)` 半透明品牌蓝 + `stroke=#00F0FF` 电光青实线（线宽随缩放成比例）+ 错位 `#4d6bfe` 虚线「幻影」轮廓，营造工程蓝图层次。
- favicon 为 50×50 viewBox，鲸鱼 bbox 约 x[0.53,49.37]、y[6.94,43.58]；排放时按 `translate(cx-wcx*s, cy-wcy*s) scale(s)` 精确居中。


## 五、如何复用 / 修改

**重新生成**（用 Python 重建 SVG，再渲染 PNG）：

```bash
# 1) 重建两个 SVG（读取 favicon.svg，写入 docs/assets/*.svg）
.venv/Scripts/python docs/assets/_build/build_svgs.py

# 2) 渲染 PNG（需 Node；resvg 渲染器脚本已备于 docs/assets/_render）
cd docs/assets/_render && npm install && node render2x.js   # 输出到 docs/assets/*.png
```

- **改文案**：`docs/assets/_build/build_svgs.py` 里 `build_social()` / `build_banner()` 的字符串（标题、slogan、chip、版本行）。中文直接改，无需动布局。
- **改配色**：文件顶部色板常量（`BG / CYAN / BRAND / ACCENT / INK / MUTED / GRID / STROKE`）。
- **改鲸鱼**：`whale_group(cx, cy, s)` 控制圆心与缩放；`s` 越大鲸鱼越大（social 240 / banner 150）。
- **网格密度**：`sparse_grid(w,h,step,opacity)` 控制背景网格疏密与透明度（当前 step 48、opacity 0.028，极淡）。

> 也可直接打开 `docs/assets/preview.html` 实时预览效果；PNG 为 @2x，直接用于 README / 社交图。


## 六、验证

- 两个 SVG 均已通过 XML well-formed 校验 + `@resvg/resvg-js` 实测渲染成 PNG（含 CJK 中文与系统字体），无语法错误。
- **重叠/越界自检（像素级）**（`docs/assets/_build/check_overlap.py` + `_render/measure_texts.mjs`）：将每个 `<text>` 用 `@resvg/resvg-js` **单独实测渲染**，取其真实墨迹包围盒（自动处理 `text-anchor=end`、`rotate(-90)`、`letter-spacing`、CJK 宽度）；chip/tag 框与鲸鱼 group 用其精确 SVG 几何。断言两两不相交（容差 0px，「文字位于自身 chip 框内」视为有意包含并排除）且全部落在画布内（含右缘：`bbox.max_x <= canvas width`）。当前**两个文件均 PASS**。运行：
  ```bash
  cd docs/assets/_render && npm install   # 首次需装 @resvg/resvg-js + pngjs
  .venv/Scripts/python docs/assets/_build/check_overlap.py
  ```
- 生成端 `_build/build_svgs.py` 在排版 tag/chip 时用同一套 resvg 实测宽度（含 letter-spacing）为框定尺寸，保证文字始终完整落在框内、互不越界。
- **同尺寸减法复核（v2 重设计）**——像素密度实测：内实块数 横幅 **4** 组（=鲸鱼/标题/slogan/meta）、社交 **7** 组（=鲸鱼/标题/副标题/3chip/版本）；非背景内容墨占比 横幅 **≈10.7%**、社交 **≈10.4%**（均远低于 15% 阈值），留白主导、无视觉过载。
- **像素采样复核**：渲染 @2x PNG 后对各间隙区采样，内容点 ≈0；此前实测曝光的「chip 拥挤/标签溢出/右缘密集」随装饰元素一并消除。
- 字体为系统栈，用户机器缺 Consolas / Microsoft YaHei 时会自动回退到等宽 / 无衬线条形栈，不会因缺字体渲染失败。
