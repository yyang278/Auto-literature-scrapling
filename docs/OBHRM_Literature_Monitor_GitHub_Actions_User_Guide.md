# OBHRM Literature Monitor GitHub Actions User Guide

本指南面向第一次使用本项目的老师和同学。你不需要安装 Codex，不需要安装 Python，也不需要在自己的电脑上配置运行环境。只要有 GitHub 账号，就可以在网页中输入关键词、时间窗口和期刊范围，自动生成一份 HTML literature report，并下载 CSV 格式的文献列表。

## 1. 这个系统能做什么

你在 GitHub Actions 页面填写：

- 最多 5 个关键词或概念，每行一个；
- 关键词匹配方式：`any` 或 `all`；
- 时间窗口和时区；
- 一个或多个 journal list；
- 可选的输出标签和公开网页地址。

系统会自动完成：

- 在所选 journal list 中按 source/concept/window 遍历 OpenAlex；
- 基于公开元数据检索并二次匹配 title、abstract、keywords；
- 生成 HTML report、Markdown report 和 CSV 文献列表；
- 生成 `obhrm_scan_trace.csv`，用于检查每个 source/concept 是否完整遍历；
- 生成 `obhrm_keyword_trends.json`，用于 HTML 报告中的关键词趋势图；
- 将 HTML 报告发布到当前 fork 仓库自己的 GitHub Pages；
- 如仓库配置了 Lark webhook，则向 Lark 发送短摘要。

重要边界：本系统不自动登录学校系统，不绕过付费墙，不处理 CAPTCHA，不下载 PDF，也不自动获取全文。报告只提供公开元数据和 DOI URL。读者如需全文，应使用自己的学校账号或其他合法权限手动访问。

## 2. 第一次使用前的准备

### 2.1 Fork 仓库

1. 打开项目仓库：`https://github.com/qlq20011120/Auto-literature-scrapling`
2. 点击右上角 `Fork`。
3. 将仓库复制到自己的 GitHub 账号下。
4. 进入自己 fork 后的仓库。

为什么需要 fork：普通用户通常不能在别人的仓库里点击 `Run workflow`。fork 到自己的账号后，你就可以在自己的仓库中运行 workflow，并把报告发布到自己的 GitHub Pages。

### 2.2 启用 GitHub Pages

1. 进入自己 fork 后的仓库。
2. 点击顶部 `Settings`。
3. 在左侧栏找到 `Pages`。
4. 找到 `Build and deployment`。
5. 将 `Source` 设置为 `GitHub Actions`。

这一步很重要。后续生成的 HTML 报告会挂载到你自己的 GitHub Pages 上。如果没有设置 GitHub Pages，workflow 可能能生成 artifacts，但公开网页链接可能打不开或显示 404。

## 3. 如何运行一次文献抓取

1. 进入自己 fork 后的仓库。
2. 点击顶部 `Actions`。
3. 在左侧选择 `Generate OBHRM Literature Report`。
4. 点击右侧或上方的 `Run workflow`。
5. 填写检索条件。
6. 再点击绿色 `Run workflow` 按钮提交任务。
7. 等待 GitHub Actions 的绿色进度条完成。

GitHub Actions 的进度条是 GitHub 自带功能，不是本项目额外做出的界面。每个步骤成功后会变成绿色。如果某一步失败，页面会显示红色叉号，并可以点进失败步骤查看 log。

## 4. Run workflow 表单填写说明

### 4.1 Keywords

最多可以输入 5 个关键词或概念。每个输入框只填一个关键词，空白输入框会被忽略。

单关键词示例：

```text
keyword_1: Presenteeism
keyword_2:
keyword_3:
keyword_4:
keyword_5:
```

上面的例子只会按 `Presenteeism` 检索，不会自动保留之前使用过的 `AI`、`LLM` 或其他关键词。

多关键词示例：

```text
keyword_1: "Business History"
keyword_2: Asia
keyword_3: Engagement
keyword_4:
keyword_5:
```

### 4.2 引号短语检索

如果希望多个单词作为固定短语按顺序出现，可以用英文双引号包起来：

```text
"Business History"
```

系统会去掉外层引号，并把它作为一个完整短语处理。也就是说，它会匹配类似 `Business History in Asia` 的文本，但不会把 `the business school and the end of history` 当作 `Business History`。

当前支持的检索语法比较克制：

- 支持普通关键词，例如 `Asia`；
- 支持多词短语，例如 `Business History`；
- 支持带英文双引号的固定短语，例如 `"Business History"`；
- 支持 `any` / `all` 两种匹配逻辑。

当前不支持完整的 Web of Science advanced search query builder 语法，例如复杂括号、通配符、字段限定符、邻近算符等。

### 4.3 Keyword matching mode

`match_mode` 有两个选项：

- `any`：或逻辑。文章命中任意一个非空关键词就会进入结果。
- `all`：并逻辑。文章必须同时命中所有非空关键词才会进入结果。

例如：

```text
keyword_1: "Business History"
keyword_2: Asia
keyword_3: Engagement
match_mode: all
```

这表示最终文章列表中的文章需要同时命中 `Business History`、`Asia` 和 `Engagement`。

### 4.4 系统检索文章的哪些位置

生产 workflow 使用 `openalex-source` 策略：

1. 先把所选 journal/platform 解析为 OpenAlex source。
2. 对每个 source、每个 keyword、每个时间窗口进行 OpenAlex 检索。
3. OpenAlex 候选检索主要依赖公开元数据中的 title/abstract search 能力。
4. 拿到候选结果后，系统会在本地再次检查文章的 `title`、`abstract`、`keywords`。
5. 最终报告和 CSV 中的 `matched fields` 会显示命中发生在哪些字段。

稳妥理解：系统会尽量在标题、摘要和关键词元数据中寻找匹配，但它依赖公开数据库提供的元数据质量。如果某篇文章没有公开摘要或关键词，系统只能基于可见字段判断。

### 4.5 Timezone

选择输入时间窗口所使用的时区：

- `Asia/Tokyo`：日本时间；
- `America/Chicago`：美国中部时间，GitHub 会按日期自动处理 CST/CDT；
- `Asia/Shanghai`：北京时间。

### 4.6 Start date / Start clock

这是检索窗口的开始时间，包含这个时间点。

推荐格式：

```text
start_date: 2026/05/18
start_clock: 00:00
```

也可以写成：

```text
start_date: 26/05/18
start_clock: 8:00
```

### 4.7 End date / End clock

这是检索窗口的结束时间，不包含这个时间点。

推荐格式：

```text
end_date: 2026/05/25
end_clock: 00:00
```

结束时间必须晚于开始时间。如果结束时间早于或等于开始时间，workflow 会失败，并显示明确错误提示。

### 4.8 Journal list checkboxes

可以同时勾选多个 journal list。系统会自动取并集并去重。

可选列表包括：

- `all-whitelist`：完整白名单，范围最广；
- `abs-4-and-4-star`：ABS/AJG 2024 中 4 和 4* 来源；
- `abs-4-star`：ABS/AJG 2024 中 4* 来源，默认勾选；
- `ft50`：FT50 来源；
- `utd24`：UTD24 来源。

如果同时勾选 `abs-4-star` 和 `ft50`，系统会搜索两个列表合并后的所有来源。

注意：这些列表之间本来就有大量重叠，所以多选后的 target sources 数量不一定会简单相加。如果多个列表中的来源高度重复，最终 source 数量可能变化很小。这不是 bug，而是去重后的并集结果。

如果一个列表都不勾选，workflow 会失败，并提示至少选择一个 journal list。

### 4.9 Output label

通常可以留空。留空时系统会自动生成报告文件夹名称。

如果希望 URL 或 artifacts 文件夹更容易识别，可以填写一个简短英文标签，例如：

```text
business-history-asia
```

### 4.10 Public site URL

通常可以留空。

留空时，系统会自动使用当前 fork 仓库的 GitHub Pages 地址：

```text
https://<github-user>.github.io/<repo-name>/
```

只有当你自己维护 Netlify 或自定义域名时，才需要填写这一项。

### 4.11 Push Lark

如果仓库已经配置 Lark webhook secrets，可以保持开启。否则即使开启，系统也会跳过 Lark 推送，不影响报告生成和 GitHub Pages 发布。

Lark 摘要只包含：

- 本次关键词；
- 时间窗口；
- 每个 journal/platform 的命中文章数；
- Public report 和 Public index 链接。

完整文献信息请打开 HTML report 阅读。

## 5. 如何查看结果

workflow 完成后，有三种查看方式。

### 5.1 查看 Public report

打开刚刚完成的 workflow run，在页面中的 summary 里查找：

```text
Public report: https://<github-user>.github.io/<repo-name>/reports/<run-folder>/
Public index: https://<github-user>.github.io/<repo-name>/
```

点击 `Public report` 可以查看本次 HTML 报告。

点击 `Public index` 可以查看这个仓库已经生成过的报告列表。列表右侧会显示运行者 GitHub 账号和运行时间；如果旧报告缺少这些元数据，会显示 `legacy report`。

如果刚运行完立刻打开链接出现 404，请等待一两分钟后刷新。GitHub Pages 部署有时会比 workflow 结束略慢。

### 5.2 下载 Artifacts

在 workflow run 页面底部找到 `Artifacts`，下载 `obhrm-report-...`。

压缩包通常包含：

- `obhrm_daily_report.md`：Markdown 报告；
- `obhrm_daily_report.html`：本次 HTML 报告；
- `obhrm_daily_records.csv`：CSV 文献列表；
- `obhrm_scan_trace.csv`：source-by-source 抓取审计表；
- `obhrm_keyword_trends.json`：趋势图数据；
- `run.log`：运行日志。

如果需要进一步分析、筛选、排序，通常使用 `obhrm_daily_records.csv` 最方便。

### 5.3 查看 Lark 摘要

如果配置了 Lark 推送，Lark 群会收到一条简短摘要。摘要用于提醒大家本次检索的关键词、窗口和期刊命中数量。完整报告仍应通过 Public report 链接查看。

## 6. HTML report 的阅读方法

### 6.1 Keyword Trajectories

如果本次运行生成了关键词趋势数据，HTML report 会出现 `Keyword Trajectories` 区块。

趋势图含义：

- 横轴是年份；
- 纵轴是该 keyword 在所选 source list 和时间窗口内的候选文献出现次数；
- 趋势图用于观察概念热度变化；
- 最终文章列表仍由 `match_mode` 的 `any` / `all` 逻辑决定。

单关键词报告只显示一张交互式趋势图，不会再显示一个总图加一个重复小图。

多关键词报告会显示：

- `Combined Keyword Trajectories` 总图；
- 每个 keyword 的小卡片；
- 点击小卡片后的交互式放大图。

### 6.2 % of keyword peak 与 Raw counts

总图和放大图都有两个显示模式：

- `% of keyword peak`：默认模式。每个 keyword 都按自己的最高年份缩放到 100%，适合比较走势形状。这个模式可以避免高频 keyword 把低频 keyword 压在横轴附近。
- `Raw counts`：原始数量模式。适合查看真实数量差距。

如果两个按钮看起来没有变化，通常说明浏览器缓存了旧版 HTML 或旧版脚本。刷新页面或重新运行 workflow 后应能看到切换效果。

### 6.3 鼠标悬停 tooltip

将鼠标移动到总图或放大图的某一年附近时，tooltip 会显示：

- 该年份每个 keyword 的候选出现次数；
- 该年份该 keyword 候选集中 OpenAlex `cited_by_count` 最高的文献信息。

这里的“引用最高”指 OpenAlex 元数据中的 `cited_by_count`，不是按发表年限校正后的 citation rate。

### 6.4 小卡片右上角图标

每个 keyword 小卡片右上角的图标只是“点击放大查看”的入口，不代表趋势方向。

### 6.5 Jump to Keyword Results

多关键词报告会在趋势图后显示 `Jump to Keyword Results`。

这个区域提供页面内快捷链接，可以直接跳转到某个 keyword 的：

- `Articles with abstracts`；
- `Missing abstracts`。

这样不需要滚动很久才能看到第二个或第三个 keyword 的结果列表。

## 7. 多关键词报告如何阅读

如果只输入一个 keyword，报告会保持简单结构。

如果输入多个 keyword：

- `At a Glance` 会按 keyword 分别统计命中文章数、有摘要文章数和缺失摘要文章数；
- `Articles With Abstracts` 会拆成多个 keyword-specific section；
- `Missing Abstract` 也会拆成多个 keyword-specific section；
- 同一篇文章如果同时命中多个 keyword，可能出现在多个 keyword section 中。

这样设计是为了方便不同老师按自己关心的概念阅读，而 CSV 仍然保持一个稳定总表。

## 8. 如何判断抓取是否完整

当前生产 workflow 使用 `openalex-source` 策略，并且 `--max-pages 0` 表示不设置手动页数上限。

系统会：

1. 将每个目标 journal/platform 解析为 OpenAlex source id；
2. 逐一检索每个 source、每个 keyword、每个时间窗口；
3. 使用 OpenAlex cursor pagination 持续翻页；
4. 直到 OpenAlex 返回没有下一页。

这意味着生产 workflow 默认不是只从前 2000 条里挑结果，而是按 source/concept/window 组合尽量完整遍历。

如果需要审计遍历过程，请查看 artifact 中的 `obhrm_scan_trace.csv`。重点字段包括：

- `api_total_count`：OpenAlex 认为该查询共有多少条；
- `fetched_count`：系统实际抓取了多少条；
- `pages_fetched`：实际翻了多少页；
- `status`：是否 `complete`；
- `query_url`：对应 OpenAlex 查询链接。

如果某一行 `status` 不是 `complete`，说明该 source/concept 可能没有完整抓完，应进一步查看 `run.log` 和 `query_url`。

## 9. 常见问题

### 9.1 为什么我在别人仓库里看不到 Run workflow

GitHub 只允许有足够权限的人在某个仓库里运行 workflow。普通老师同学应先 fork 仓库，然后在自己的 fork 中运行。

### 9.2 为什么 Public report 打开是 404

常见原因：

- GitHub Pages 还没有部署完成，请等待一两分钟后刷新；
- `Settings` -> `Pages` 的 `Source` 没有设置为 `GitHub Actions`；
- workflow 没有完整运行成功；
- 打开的不是自己 fork 仓库对应的 Pages 链接。

### 9.3 为什么结果非常多

可以尝试缩小检索范围：

- 使用 `abs-4-star` 而不是 `all-whitelist`；
- 使用 `all` 而不是 `any`；
- 缩短时间窗口；
- 使用更具体的关键词或短语；
- 使用英文双引号输入固定短语，例如 `"Business History"`。

### 9.4 为什么 abstract 特别长

系统会尽量保留公开元数据 API 返回的 abstract 信息。目前不会自动截断 abstract，因为截断可能损失科研判断所需的信息。快速浏览时，可以先看 title、journal、publication date、DOI URL、matched concepts 和 matched fields。

### 9.5 Set up Python 阶段出现 pip cache warning 是不是失败

如果看到类似：

```text
Warning: Failed to restore: The operation was aborted.
pip cache is not found
```

通常只是 GitHub Actions 恢复 Python 依赖缓存失败，不代表抓取代码失败。影响通常只是这次依赖安装慢一点。只要后续步骤继续运行，并且最后没有 `Process completed with exit code 1`，一般可以忽略。

## 10. 推荐填写模板

### 10.1 精准短语检索

```text
keyword_1: "Business History"
keyword_2: Asia
keyword_3:
keyword_4:
keyword_5:
match_mode: all
timezone: Asia/Tokyo
start_date: 1970/01/01
start_clock: 00:00
end_date: 2026/06/01
end_clock: 00:00
journal lists: abs-4-star + ft50
```

### 10.2 单关键词检索

```text
keyword_1: Presenteeism
keyword_2:
keyword_3:
keyword_4:
keyword_5:
match_mode: any
timezone: Asia/Tokyo
start_date: 2026/05/18
start_clock: 00:00
end_date: 2026/05/25
end_clock: 00:00
journal lists: abs-4-star
```

### 10.3 多关键词或逻辑检索

```text
keyword_1: AI
keyword_2: LLM
keyword_3: "Large Language Model"
keyword_4:
keyword_5:
match_mode: any
timezone: Asia/Tokyo
start_date: 2026/05/18
start_clock: 00:00
end_date: 2026/05/25
end_clock: 00:00
journal lists: abs-4-star + ft50 + utd24
```

## 11. 最简流程回顾

```text
进入自己 fork 后的仓库
  ↓
Settings -> Pages -> Build and deployment -> Source -> GitHub Actions
  ↓
Actions -> Generate OBHRM Literature Report
  ↓
Run workflow
  ↓
填写 keywords、match mode、timezone、time window、journal lists
  ↓
等待绿色进度条完成
  ↓
打开 summary 中的 Public report 链接查看 HTML 报告
  ↓
下载 Artifacts，获取 CSV 文献列表和 trace 审计文件
```
