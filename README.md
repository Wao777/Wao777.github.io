# 个人作品主页

零构建、零依赖的静态站点。原生 HTML / CSS / 少量 JS，直接托管在 GitHub Pages。

## 目录结构

```
.
├─ index.html                 主页：Hero（标题 + 今日日报卡）→ 作品网格 → 小工具行 → 一句话主张
├─ reports/latest.html        今日日报，由 n8n 每日覆盖，地址固定
├─ scripts/publish.py         发布脚本：校验 → 覆盖 → commit → push
├─ scripts/make_icons.py      图标生成器：改配色或尺寸后重跑
├─ scripts/inject_meta.py     批量注入 canonical / og / 图标链接（幂等，带 --dry）
├─ _incoming/                 n8n 的中间产物与发布日志（不参与部署）
├─ works/<slug>/index.html    每个作品一个目录，链接一律写全 ./works/<slug>/index.html
├─ assets/
│  ├─ css/tokens.css          设计令牌：颜色、圆角、阴影、动效。改配色只动这里
│  ├─ css/main.css            主页样式 + 响应式
│  ├─ css/work.css            详情页样式（README 版式）
│  ├─ js/main.js              主题切换 / 滚动入场
│  ├─ js/doc.js               详情页：代码复制 / 目录跟随高亮
│  └─ img/                    站点图标：favicon.svg / favicon.ico / apple-touch-icon.png
├─ 404.html                   独立样式，不依赖外部资源
├─ robots.txt                 允许全站抓取，声明 sitemap 地址
├─ sitemap.xml                8 个页面，新增作品要手动加一条
├─ .nojekyll                  禁用 Jekyll 处理
└─ CNAME                      由 GitHub 后台填域名时自动生成，不要手动先提交
```

## 本地预览

直接双击 `index.html` 即可——所有资源都是相对路径，`file://` 下能正常跑。
要走真实 HTTP（验证 404、路径行为），用任意静态服务器：

```bash
python -m http.server 8080
```

### 链接必须写全 index.html（重要）

站内所有页面链接一律写成 `./works/<slug>/index.html`，**不要写成 `./works/<slug>/`**。

原因：以斜杠结尾的目录链接，在 GitHub Pages 上会自动补 `index.html`，但用 `file://` 双击打开时浏览器只会列出目录内容，看起来像"没接上前端"。写全文件名两边都能走。

同理，返回主页写 `../../index.html#works`，而不是 `../../#works`。

## 今日日报（n8n 自动更新）

首页 Hero 右侧那张卡固定在 `reports/latest.html`，**这个地址永不改变**，所以日报换新时首页一个字都不用改。

链路（**一条工作流跑完，不用手工配节点**）：

```
开机 / 登录
  → Windows 计划任务 n8n-autostart 跑 n8n-autostart.pyw
      静默拉起 n8n → 等 healthz 就绪 → POST webhook
  → 开机触发（Webhook，POST /webhook/daily-brief-run）
  → 守卫 1：查上次运行，打印 <n8n 目录>\out\.last-run 里的日期
  → 守卫 2：等于今天就整链结束（零点几秒，不抓网不调 AI）
  → 生成链：12 家 RSS → 解析合并 → 条数校验 → 天气 → AI 打分 → AI 整理 → 渲染 HTML
  → 转 HTML 附件
  → 写日报文件：写 <n8n 目录>\out\daily.html（白名单内，见下方环境变量）
  → 推送上线：执行 scripts/publish.py
  → 校验 → 覆盖 reports/latest.html → commit → push（SSH 443）
  → 记下今天：把今天日期写回 <n8n 目录>\out\.last-run
  → GitHub Pages 约 1 分钟后发布
```

整条链共 **24 个节点**（原 19 节点生成链 + 写盘 / 推送 / 记账各 1 + 守卫 2）。

**一天只跑一次**：没有定时任务，靠「开机叫醒 + 日期守卫」。`.last-run` 里存的是**上次成功发布**的日期，等于今天就整链结束。所以一天开几次机都只出一期；而失败的那次不算「已跑」，下次开机自动重试——宁可可重试，也不要因为一次抓取失败整天没报。

**为什么不用定时触发**：n8n 没有「开机触发」这种东西，Schedule Trigger 只能按 cron 跑。7 点开机不现实，所以触发换成 Webhook，由开机脚本等 n8n 就绪后调一次。

**开机脚本只对 404 重试**：n8n 刚起来时 webhook 还没注册，会返回 404，这时重试是安全的（工作流根本没开始跑）；一旦拿到任何响应就停止，绝不重复 POST——否则一次开机可能变成两次执行。

**仓库里不放 n8n 的工作流 JSON**：这个仓库是站点本身（页面 + 图片 + `publish.py`）。工作流只活在 n8n 自己的库里，要公开存档另开仓库。

### 已经做完的一次性准备

1. 仓库 `Wao777.github.io` 已建，`main` 已首推，本地 `origin` 指向 `ssh://git@ssh.github.com:443/Wao777/Wao777.github.io.git`（22 端口在本机不通，必须走 443）。
2. 推送走 SSH key，n8n 里那次 push 不需要交互式登录。
3. `<n8n 目录>\start-n8n.bat` 已加 `set NODES_EXCLUDE=[]`——n8n 2.x 默认封禁 Execute Command 节点，不加这一行工作流会报「Unrecognized node type」。
4. 计划任务 `n8n-autostart`（登录触发）指向 `pythonw.exe <n8n 目录>\n8n-autostart.pyw`；它调的是无 `pause` 版本的 `<n8n 目录>\start-n8n-task.bat`，日志写到 `<n8n 目录>\out\n8n-service.log`（**这两个 bat 必须保持 CRLF**，LF 会让 cmd 漏掉环境变量，数据跑到 C: 盘）。
5. `<n8n 目录>\mark-run.py` 与 `<n8n 目录>\read-last-run.py` 分别负责写、读 `.last-run`。

### 工作流需要的两个环境变量

| 变量 | 值 | 为什么 |
|---|---|---|
| `NODES_EXCLUDE` | `[]` | n8n 2.0 起默认封禁 Execute Command 与 Local File Trigger，空数组才放开 |
| `N8N_RESTRICT_FILE_ACCESS_TO` | `<n8n 目录>\out` | 写盘白名单。不在白名单里的路径会报「Access to the file is not allowed」，所以日报先落在 `<n8n 目录>\out` 再由脚本搬走 |

两个都已经写进 `start-n8n.bat`。**用命令行 `n8n execute` 测试时要自己带上这两个变量**，否则报的错跟工作流本身无关。

### 尾部四个节点

| 节点 | 类型 | 配置 |
|---|---|---|
| 转 HTML 附件 | Convert to File | 转成 `text/html` 二进制，属性名 `data` |
| 写日报文件 | Read/Write Files from Disk | Operation `write`，File Name `<n8n 目录>\out\daily.html` |
| 推送上线 | Execute Command | 见下方命令 |
| 记下今天 | Execute Command | 跑 `mark-run.py`，写 `.last-run` |

Execute Command 里把路径写死，别用 `{{ $json.xxx }}` 拼——经过二进制节点后路径经常丢：

```cmd
%USERPROFILE%\AppData\Local\Programs\Python\Python314\python.exe "<站点目录>\scripts\publish.py" "<n8n 目录>\out\daily.html"
```

路径含中文，如果 n8n 报「系统找不到指定的路径」，先确认引号没被吃掉；仍不行就把整个站点目录挪到纯英文路径下（GitHub Pages 不关心本地路径）。

### publish.py 做了什么

1. 校验源文件：存在、大于 512 字节、内容含 `<html>` 或 `<body>`——**这层是防止 n8n 生成失败时把一页错误信息推上线**
2. 覆盖 `reports/latest.html`
3. `git add` → 有变化才 `commit` → `push`
4. stdout 输出一行 JSON，同时追加到 `_incoming/publish.log`

返回码：

| status | 退出码 | 含义 |
|---|---|---|
| `published` | 0 | 已发布，带上 commit 短 SHA |
| `no_change` | 0 | 内容与仓库一致，跳过提交（不算失败） |
| `missing_src` / `too_small` / `not_html` | 3–5 | 源文件有问题，停下 |
| `no_repo` / `no_remote` | 6–7 | 仓库没初始化或没配远端 |
| `push_failed` | 10 | 推送失败，多半是凭据或网络 |

手动测一次：

```cmd
python scripts\publish.py "路径\到\某个日报.html"
```

返回 `published` 或 `no_change` 就说明链路通了。

> 顺带一提：`no_change` 设计成成功而不是失败，是因为每天内容有可能几乎不变。若你希望这种情况也算异常，把退出码改掉即可。

**首页那张卡的边界**：Hero 右侧「今日日报」卡负责展示日报内容（指向 `reports/latest.html`）；网格里的 02 号卡《n8n 日报流水线》是技术展示卡，讲的是这条链怎么搭的，详情页在 `works/daily-pipeline/`。两者互不引用——别把日报正文塞进 02 号卡，也别在日报页里写流水线细节。

**详情页分两段讲**：`#flow-gen` 先讲生成（19 个 n8n 节点：12 家源 → 解析合并 → 条数校验 → 天气 → AI 打分 → AI 整理 → 渲染 HTML），`#flow-pub` 再讲发布（写盘 → 校验 → 覆盖 → 提交推送 → Pages）。生成那段是重点，别被发布那段挤回次要位置；两段的节点表都以「出问题会怎样」为第三列，因为这条链的失败路径比成功路径更需要解释。

## 新增一个作品

详情页是 **README 结构**，固定七节，顺序不要乱：

```
这是什么 → 环境要求 → 安装 → 快速开始 → 命令与参数 → 常见问题 → 更新记录
```

非工具类作品（三维场景、站点本身）可以把中间几节换掉，但要保留「这是什么 / 常见问题 / 更新记录」这头和尾。

### 步骤

1. 复制 `works/desktop-ticker/` 整个目录，改名为新 slug（小写英文 + 连字符）。
2. 改目录内 `index.html`：
   - `<title>`、`<meta description>`、`<h1>`、`.doc__tagline`
   - 四个 `.badge`：版本 / 许可 / 平台 / 依赖，色点分别用 `--c2`、`--c1`、`--pop-b`
   - `.doc__col > .doc__actions` 里的源码位（这一条贴在正文卡上方，滚动时吸附在导航下方），二选一：
     - **有公开仓库**：`<a class="dbtn dbtn--ghost" href="仓库地址" target="_blank" rel="noopener" title="将跳转到 GitHub 仓库（新窗口）">源码 · GitHub ↗</a>`
     - **暂无仓库**：`<span class="dbtn dbtn--off" title="本项目暂不提供公开源码">源码暂不提供</span>`（虚线边静态标签，不可点、不带上箭头）
   - 每一节 `<h2 id="xxx">` 与正文；左侧 `.toc__list` 的 `href="#xxx"` 必须一一对应
   - `.toc__meta` 两条：规模 / 许可
   - `.pager` 的上下篇链接，保持首尾成环
3. 在主页 `index.html` 的作品网格里复制一段 `<article class="card reveal">`，修改：
   - `href="./works/<slug>/index.html"`
   - `aria-label` 与卡片标题、简介、标签
   - `style="--c1:#...; --c2:#..."` —— 这组色决定该卡的色带、封面渐变、装饰圆环，详情页的色带与标题方块也取自它
   - `class` 里的尺寸类（见下表）

**目录是写在 HTML 里的，不是 JS 生成的**，所以没有 JS 也能跳转；`doc.js` 只负责滚动时高亮当前节。改标题时记得同步 `.toc__list`。

### 卡片尺寸类

网格是 6 列，靠 `grid-column: span N` 分配宽度。当前排布：

| 位置 | 卡片 | 类名 | 跨列 | 封面高 |
|---|---|---|---|---|
| 第 1 张（通栏） | 内容聚合 | `card--wide` | 6 | 344px |
| 第 2 张（半宽） | n8n 日报流水线 | `card--mid` | 3 | 248px |
| 第 3 张（半宽） | 桌面常驻盯盘条 | `card--mid` | 3 | 248px |

封面高度是「作品区一屏装下」算出来的：**01 的 344px 是下限**，它按 1080×386 的概念图画，再矮会切掉窗口顶栏的圆点。加卡片请新起一行，别往回加高。

六列总宽恒为 6，所以 **换卡片数量时要保证每行加满 6 列**，否则右侧会留空。两张一行是 `3+3`，通栏独占一行是 `6`。
`card--sm`（跨 2 列、封面 240px）样式仍在：需要三等分一行时用 `2+2+2` 即可，无需新写 CSS。

**配色只用四色**：`#1B4DFF` 蓝 / `#FF4D2E` 橙红 / `#FFD400` 明黄 / `#12D6A0` 青绿。
卡片色带是两色渐变，从四色里取两个组合使用，别引入第五个颜色。

### 技术展示卡（封面画链路）

不是每张卡都有产物可以截图。讲「一条链」的卡可以把流程直接画在封面上——纯 CSS，无图片：

```html
<div class="card__cover">
  <span class="card__num">02</span>
  <div class="card__flow" aria-hidden="true">
    <span class="flow__step"><b>开机</b><i>自动触发</i></span>
    <span class="flow__line"></span>
    <span class="flow__step"><b>n8n</b><i>取数排版</i></span>
    <span class="flow__line"></span>
    <span class="flow__step"><b>publish.py</b><i>校验提交</i></span>
    <span class="flow__line"></span>
    <span class="flow__step"><b>Pages</b><i>每日上线</i></span>
  </div>
</div>
```

- **四段为宜**：`<b>` 是等宽字体的节点名（保持短，最长一个 `publish.py`），`<i>` 是两到四字的动作；再多就会挤成一团。
- 链路条水平居中于封面，`≤700px` 自动隐藏（两列时卡宽只剩三百出头），只留大号序号。
- 颜色全部由 `--ink` 混合得出，深色模式不用另写一套。
- 这类卡讲的是**怎么做的**，与 Hero 的「今日日报」卡（展示日报内容）是两回事，别把日报正文塞进卡片。

### 新增一个小工具

小工具不占大卡：大卡放作品，工具压成一行窄卡，位置固定在大卡网格之后、一句话主张之前。
小卡整张可点，点进去是和小工具同名目录下的详情页（同样是 README 版式）。

改 `index.html` 里的 `.tools__row`，追加一个 `<li>`：

```html
<li class="tool" style="--c1:#12D6A0">
  <a class="tool__link" href="./works/<slug>/index.html">
    <span class="tool__name">工具名<span class="tool__tag">Windows</span></span>
    <span class="tool__desc">一句话说清它替你省掉了什么。</span>
  </a>
</li>
```

- `--c1` 决定名称前的色点与 hover 文字色，只能取四色之一（蓝 / 橙红 / 明黄 / 青绿），不引入新色。
- 一行按 232px 起排、单张最宽 296px，**加几张就往右排几张**，不用改任何布局；≤560px 自动转单列。
- 详情页按「新增一个作品」的同一套骨架写，但可以更短：小工具通常四到六节就够（这是什么 / 界面 / 怎么判 / 修复与回滚 / 命令行 / 安全与限制）。
- 新增小工具后记得接上 `<nav class="pager">` 的翻页环，并同步本文档的「当前排布」表述。
- 卡片没有封面区，所以 `.card__num` 序号、标签列表都用不上，别照抄作品卡的写法。
- 当前小工具四件，按此顺序排开：断网自动修复 / 多屏设置 / 护眼提醒 / 涨停速览。

## 换成你自己的信息

| 位置 | 改什么 |
|---|---|
| 导航 `.brand` | 现为 `Wao 的个人站点`（八个页面都已统一）；导航只有品牌与主题切换，没有链接 |
| `index.html` Hero 标题 | 「把零散的想法，做成能用的东西。」 |
| `index.html` 一句话主张（`#about`） | 「把重复动作变成脚本，把数据变成界面。」 |
| 每个 `works/<slug>/index.html` 的源码位 | 有仓库 → `源码 · GitHub ↗` 指向真实地址（`target="_blank"`）；没有 → 保持 `源码暂不提供` 静态标签，别做成点了没反应的假按钮 |
| 每个详情页的版本号与 `.toc__meta` | 换成真实版本与规模（2026-10 起已去掉「更新」一项，别再补回去） |
| 所有页面的页脚 | 只有版权行：`© 2026 · 由 AI 生成 · 托管于 GitHub Pages`；年份可改，页脚导航（作品/关于/邮件）已删除，别再补回 |

## 部署到 GitHub Pages

```bash
git init
git add .
git commit -m "init portfolio"
git branch -M main
git remote add origin https://github.com/<用户名>/<仓库名>.git
git push -u origin main
```

然后在仓库 **Settings → Pages**：

- Source 选 **Deploy from a branch**
- Branch 选 `main`，目录选 `/ (root)`
- 保存后等 1 分钟左右，访问 `https://<用户名>.github.io/<仓库名>/`

> 仓库名直接用 `<用户名>.github.io` 的话，站点在根路径，URL 更短，也不用处理子路径问题。

`.nojekyll` 必须保留。没有它，GitHub 会跑一遍 Jekyll，以下划线或点开头的资源可能被忽略。

## 绑定自定义域名

1. 仓库根目录新建 `CNAME` 文件（无扩展名），内容只写域名，不带协议、不带结尾斜杠：

   ```
   www.example.com
   ```

2. DNS 记录：

   | 场景 | 记录类型 | 主机 | 值 |
   |---|---|---|---|
   | 子域（www.example.com） | CNAME | www | `<用户名>.github.io` |
   | 根域（example.com） | A | @ | `185.199.108.153` |
   | | A | @ | `185.199.109.153` |
   | | A | @ | `185.199.110.153` |
   | | A | @ | `185.199.111.153` |

3. 回 **Settings → Pages → Custom domain** 填入域名并保存（会自动写回 `CNAME` 文件）。
4. 等 DNS 生效（几分钟到 24 小时），再勾选 **Enforce HTTPS**。证书是自动签发的，但要先解析通过才能勾。

**注意**：`CNAME` 文件一旦丢失，GitHub 每周会把自定义域名重置回默认地址。用 Actions 部署时，务必确保它在构建产物的根目录。

## 响应式断点

桌面端是主场景，以下按 1440 宽设计：

| 断点 | 表现 |
|---|---|
| ≥ 1441px | 容器最大 1280px，保持桌面排布 |
| 1101–1440px | 六列网格不变，Hero 双栏（标题 + 日报卡），卡片按 6/3/2 跨列 |
| 901–1100px | 收成两列等宽，尺寸类失效；Hero 仍双栏，只收紧间距与标题字号 |
| 769–900px | Hero 转单栏，日报卡落到标题下方 |
| ≤ 768px | 卡片封面对齐 232px |
| ≤ 560px | 单列，封面 208px |

详情页另有三个断点：

| 断点 | 表现 |
|---|---|
| ≤ 1024px | 目录栏 236 → 208，正文卡内边距收紧 |
| ≤ 900px | 目录卡隐藏，正文占满一栏；工具条仍贴右 |
| ≤ 560px | 预览图改 4:3，代码块字号降到 .79rem |

> 移动端（≤768px）目前是可用状态但未细调，计划后做。

关键实现：桌面网格用固定 6 列 + `span` 分配，每行必须加满 6 列；字号全部 `clamp()` 流式缩放。
详情页两栏是 `236px + 1fr`，目录卡 `position: sticky`，正文卡限宽 48rem。

「返回作品 / 源码」两个按钮在右列顶部，右缘与正文卡对齐，`position: sticky; top: calc(var(--nav-h) + 14px)` 常驻。`doc.js` 在它吸附后加 `.is-stuck`：换成实底白胶囊、出现细描边与阴影，按钮同时收紧到 32px 高，减少对正文的遮挡。

## 无障碍与性能基线

- 语义标签、`aria-label`、`aria-pressed`、`aria-current`、跳转链接
- 键盘可达，`:focus-visible` 有明确轮廓
- `prefers-reduced-motion` 全站关闭动效
- 无外部字体、无框架；CSS 约 34KB，JS 约 6KB（main.js + doc.js）
- 无 JavaScript 时全部内容与跳转依然可用：目录写在 HTML 里，代码块可手动选中复制
- 详情页可键盘 Tab 到「复制」按钮与每个目录项，`:focus-visible` 有轮廓
