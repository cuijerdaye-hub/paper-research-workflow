---
name: cnki-research-workflow
description: 面向 Codex 的中英文联合学术检索与中国知网（CNKI）端到端研究工作流。Use when Codex needs to search, merge, screen, and cite Chinese and English literature; run CNKI searches; use paper-search-pro/OpenAlex/Crossref/Semantic Scholar for English papers; apply CSSCI/北大核心/CSCD/EI/JCR/SJR filters; verify metadata or authorized full text; export GB/T 7714/BibTeX/RIS/CSV; or hand results to Zotero. Enforces separate bilingual query plans, DOI/title deduplication, captcha/login/rate-limit stops, and explicit metadata-versus-full-text evidence labels.
---

# 中英文联合文献研究工作流

将任务拆成“中文知网检索、英文开放数据库检索、统一去重筛选、全文核验、引用交付”五层。中英文必须分别规划查询，不把中文检索式直接标成英文空间，也不把 `--lang both` 当作自动翻译。

## 能力路由

1. **中文检索**：加载 `$cnki-search`，通过本机 `cnki` CLI 串行、小批量检索。
2. **英文多源检索**：优先加载 `$paper-search-pro`。由本工作流调用时使用其 headless `agent_search` 通道；运行前阅读其 `references/agent_mode.md` 与 `references/setup.md`，始终从用户工作目录执行。
3. **英文降级路径**：`paper-search-pro` 未安装、配置不完整、限流或零命中时，明确报告降级原因，再加载 `$paper-lookup` 使用 OpenAlex/Crossref/Semantic Scholar 等可用来源。不得伪装成完整多源检索。
4. **登录态页面与来源筛选**：需要 CNKI 登录态、核心来源或授权下载时加载 `$chrome:control-chrome`。
5. **全文阅读与 PDF 校验**：下载成功后加载 `$pdf:pdf`；先检查文件类型，再提取文本并按需渲染关键页面。
6. **引用校验**：有 DOI 时加载 `$citation-management` 核对元数据；中文无 DOI 文献以知网详情页为主，不用 Crossref 猜测缺失字段。
7. **Zotero**：仅在用户要求时加载 `$cli-anything-zotero`，先检查 Zotero 和 Local API 状态，再执行导入。

详细路由见 [references/routing.md](references/routing.md)；英文专用规则见 [references/english-routing.md](references/english-routing.md)。

## 工作流

### 1. 定义证据边界

从用户请求提取：中文/英文/双语范围、主题词、方法词、应用场景、年份、文献类型、来源层次、数量、是否需要全文、引用格式和交付目录。缺失项不影响初筛时采用保守默认值：按用户语言检索、近 5 年、20 条、仅候选清单。

不要静默放宽年份、来源层次或方法要求。条件过窄时先报告命中情况，再提出一个最小放宽方案。

### 2. 制定分层查询

中文和英文各自至少准备两层查询：

- 精确组合：主题 + 方法或场景。
- 放宽组合：分别检索主题域、方法域，再在本地交叉筛选。

英文检索式由研究概念翻译和扩展生成，保留项目管理、理论、方法和行业场景的同义表达。短语零命中时逐步拆词，不要一次堆叠大量同义词。记录每条查询、语言、日期、来源、过滤条件和命中数。

### 3. 中文 CNKI 初筛

先运行：

```powershell
cnki --version
cnki search "<query>" --field=topic --sort=relevance --size=20 --format=json
```

规则：

- 每次 10–30 条；只在用户明确要求时扩大。
- 所有知网请求串行执行，禁止并发批量搜索。
- 需要引用时可用 `--format=citation`，但不得直接把输出视为终稿。
- 对论文详情只使用检索返回的 URL；不要手工重建。
- 遇到退出码 2、验证码、登录要求或权限错误时停止，不伪造结果。不同 `cnki` 版本的“无结果”退出码可能不同，还要识别 stderr 中的 `no results matched the query`。

将各查询的 JSON 保存到 `<workspace>/work/cnki/<slug>/raw/`。使用候选合并脚本生成本地清单：

```powershell
python "<skill-root>/scripts/merge_candidates.py" `
  --input query-a.json query-b.json `
  --output candidates.json `
  --sort cited
```

### 4. 英文多源初筛

优先使用 `paper-search-pro` 的结构化通道：

```powershell
$env:PYTHONUTF8 = "1"
$env:PYTHONPATH = "$env:USERPROFILE\.codex\skills\paper-search-pro"
python -m scripts.agent_search "<English query>" `
  --lang en --verify --min-relevance 0 `
  --year-min 2016 --limit 100 |
  Out-File -Encoding utf8 english-candidates.json
```

规则：

- 必须传入真正的英文检索式；`--lang en` 不负责翻译。
- `relevance.method=heuristic_v1` 只是排序底线，不是最终相关性判断；必须结合题名、摘要和章节主题进行人工语义分级。
- 真实研究默认迭代多个英文检索式，直到新一轮不再增加高相关候选；不能把单次查询冒充穷尽检索。
- 对拟引用记录优先使用 `--verify-refs` 或 `$citation-management` 复核 DOI、作者、年份和期刊。
- OpenAlex/Semantic Scholar 限流、配额不足或配置缺失时停止该来源，保留错误记录并按英文降级路径处理。
- Windows 下先设置 `PYTHONUTF8=1`，避免 Python 按 GBK 输出特殊字符时中断；PowerShell 不要用裸 `>` 保存 JSON，它可能生成 UTF-16。使用 `Out-File -Encoding utf8`，合并脚本同时兼容 UTF-8 BOM 与 UTF-16 BOM。

### 5. 合并、去重与候选筛选

使用统一脚本合并中英文原始结果：

```powershell
python "<skill-root>/scripts/merge_bilingual_candidates.py" `
  --cnki query-a.json query-b.json `
  --english english-a.json english-b.json `
  --output candidates.json `
  --csv candidates.csv
```

英文优先按规范化 DOI 去重；无 DOI 时按规范化题名 + 年份去重。中文按题名 + 年份去重。中英文题名仅在 DOI 相同时自动合并，避免把译名相近但不同的文章误合并。

英文输入可直接使用 `paper-search-pro` 信封、Crossref `message.items`、Semantic Scholar `data`、OpenAlex `results` 或顶层数组。未知对象结构必须报错，禁止静默按零条处理。

按题名、作者、年份去重，并从以下维度判断：主题贴合、方法贴合、应用场景、来源层次、年份、被引/下载、元数据完整性。被引量和下载量只能作为辅助证据。

默认将候选标注为：`主参考`、`辅助参考`、`背景材料`、`待核验`、`剔除`。详细量表见 [references/quality-safety.md](references/quality-safety.md)。

### 6. Chrome 精筛

仅对短名单使用浏览器。开始前加载 `$chrome:control-chrome`，优先复用用户现有登录态；不得读取 Cookie、密码、Local Storage 或浏览器配置。

浏览器阶段适用于：

- CSSCI、北大核心、CSCD、EI 等来源筛选。
- 期刊检索、收录情况、影响因子和刊期目录。
- 完整摘要、关键词、基金、分类号和机构信息核验。
- 用户授权范围内的 PDF/CAJ 下载。

不要把 CLI 返回的会话型详情 URL 直接跨会话复用。优先用“题名 + 第一作者 + 年份”在已登录浏览器中重新定位。

只关闭本任务创建的标签页。页面出现验证码时请用户在 Chrome 中手动完成；用户确认后再继续。

### 7. 授权下载与全文核验

仅下载经过初筛的少量候选。下载前确认：用户已登录、账号或机构具备权限、详情页题名匹配、页面存在合法下载入口。

- 优先 PDF；只有用户接受且 PDF 不可用时才尝试 CAJ。
- 不绕过付费墙、验证码、登录或下载权限。
- 同类页面或下载失败最多尝试 3 次，之后停止并报告。
- PDF 文件必须以 `%PDF` 开头；HTML、JSON 或登录页不得当作论文。

对合法 PDF 加载 `$pdf:pdf`，阅读摘要、研究设计/模型、变量或主体、结论与局限。不要仅凭标题、摘要、被引量或下载量认定论文适用。

### 8. 引用与 Zotero

引用交付前核对：文献类型、作者、题名、来源、年份、卷期、页码、DOI。特别检查：

- 学位论文应为 `[D]`，不要沿用错误的 `[J]`。
- 网络首发时间不能冒充卷期或页码。
- 缺失字段标记为“待核验”，不得猜测。

有 DOI 时用 `$citation-management` 验证；没有 DOI 的中文文献以知网详情页和期刊官网为主。用户要求导入 Zotero 时，再用 `$cli-anything-zotero` 导入结构化 JSON、RIS 或 BibTeX。

### 9. 报告

至少包含：

| 字段 | 要求 |
|---|---|
| 检索记录 | 查询式、日期、过滤条件、命中数 |
| 候选信息 | 语种、题名、作者、来源、年份、DOI、被引/下载 |
| 证据等级 | 主参考、辅助参考、背景材料、待核验或剔除 |
| 理由 | 对应主题、方法和场景的具体判断 |
| 全文状态 | 未下载、已下载、格式校验、已核验 |
| 引用状态 | 已核对、缺字段或待人工复核 |

最终结论必须区分“搜索元数据支持”和“全文证据支持”。

## 安全与反爬

- 串行、小批量、按需访问；不建立持续爬虫。
- 不破解验证码，不伪造登录态，不提取或复用用户凭证。
- 验证码、登录、权限或明显限流出现时立即暂停。
- 详情页与下载比搜索更敏感；只对短名单执行。
- 不并发运行多个 CNKI Skill 或浏览器检索任务。
- 英文侧只使用公开 API 或用户已配置的合法服务，不抓取 Google Scholar 页面，不绕过 API 配额或访问控制。
- 中英文原始记录、筛选结果和检索日志分目录保存，任何降级或跳过均写入报告。

## 来源边界

本 Skill 是原创编排层，不内置第三方仓库代码。`ExquisiteCore/CNKI-search` 和 Apache-2.0 的 `O0000-code/paper-search-pro` 均作为可选外部运行时调用；不复制其实现。`cookjohn/cnki-skills` 仅提供浏览器任务类别参考；`LongMarching/cnki-search-skill` 和 `cnki-trawl-pick-skill` 因许可证限制只用于能力分析，不复制、修改或再分发其实现。详见 [references/routing.md](references/routing.md)。
