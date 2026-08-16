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


## 二、构图

### ① 社交预览图 1200×630
- **左：鲸鱼卡**（470×412）——官方鲸鱼居中，蓝色半透明浮层 + 电光青实线描边 + 蓝品牌蓝虚线「幻影」底衬；卡片四周准星括号 + 内层虚线衬框；卡顶 `MOUNT / WHALE.SVG`、卡底 `SCALE 1:1 / OFFICIAL MARK` 技术标注。
- **右：标题块**——顶部 `SPEC / BLUEPRINT COVER v2.0` + 带刻度的横线；主标题 `DSH Desktop`（96px 粗体，DSH 青 / Desktop 白）；中文副标题「DeepSeek Harness 桌面版」（40px）；分隔线 + 橙色菱形节点。
- **价值三角**：三个卡片型 chip「一键启动 · 远程访问 · 插件市场」，末位用橙色强调。
- **底部标签带**：`[v2.0] [Node → DSH → 插件 自动引导] [服务守护]`（等宽字体，功能标签体系）。
- **工程图装饰**：左上 `[FIG.01]`、右上 `[STATUS: ACTIVE]` 橙色印章、下缘 1200px 尺寸刻度、右缘 630px 竖标、右下坐标 `@ 1200 x 630`。
- 四周均留有 >55px 安全边距，GitHub 压缩后小字仍清晰（标签字号 24px+、高对比）。

### ② README 横幅 1280×320
- **左：鲸鱼**（约 116px）居中于竖向准星圈 + 基准十字；`WHALE.SVG` 版权标注。
- **中：标题块**——`DSH Desktop`（84px）+ 中文 slogan「一键启动 · 零配置 · 远程访问 · 服务守护」（36px）+ 英文导语（等宽小字），整体垂直居中。
- **右：三级引导流水线**——`Node.js → DSH → 插件` 三个流程框（橙色箭头连接），下接 `3-STAGE` 刻度线 + `服务守护` / `v2.0` 标签。
- 上下两条 mono 头尾行（左：`DSH-DESKTOP / RELEASE 2.0`；右：`1280 × 320`），左右准星括号框。


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

- **改文案**：`docs/assets/_build/build_svgs.py` 里 `build_social()` / `build_banner()` 的字符串（标题、slogan、标签、坐标）。中文直接改，无需动布局。
- **改配色**：文件顶部色板常量（`BG / CYAN / BRAND / ACCENT / INK / MUTED / GRID / STROKE`）。
- **改布局 / 尺寸**：调整左右栏起点（如 `rx`、`lx/ly/lw/lh`、`px/py`），或直接改 `W/H` 画布并同步 PNG 输出。
- **改鲸鱼**：`whale_group(cx, cy, s)` 控制圆心与缩放；`s` 越大鲸鱼越大。
- 两图共用同一批函数（`bracket` 准星、`dataline` 刻度、`tagchip` 标签、`grid`），改一处即同步两图，保证视觉一致。

> 也可直接打开 `docs/assets/preview.html` 实时预览效果；PNG 为 @2x，直接用于 README / 社交图。


## 六、验证

- 两个 SVG 均已通过 XML well-formed 校验 + `@resvg/resvg-js` 实测渲染成 PNG（含 CJK 中文与系统字体），无语法错误。
- 比例 / 安全区 / 文字可读性已用像素分析核对：主体均落在安全区内（四周 ≥40px），标题与标签字号符合 ≥28px 的要求，GitHub 压缩缩略图仍可读。
- 字体为系统栈，用户机器缺 Consolas / Microsoft YaHei 时会自动回退到等宽 / 无衬线条形栈，不会因缺字体渲染失败。
