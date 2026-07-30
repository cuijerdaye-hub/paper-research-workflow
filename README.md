# CNKI Research Workflow for Codex

面向 Codex 的中英文联合文献研究工作流。中文侧以中国知网为主，英文侧组合 OpenAlex、Crossref、Semantic Scholar、PubMed 和 arXiv 等来源；随后统一去重、筛选、全文核验、校正引用并交接 Zotero。

## 核心能力

- 分别生成中文和英文检索式，不把机器翻译结果直接当作最终英文检索式。
- 使用本机 `cnki` CLI 对 CNKI 做结构化、小批量初筛。
- 调用 `paper-search-pro` 对英文数据库做可追溯的无头检索。
- 英文主检索不可用、限流或零结果时，切换到 Codex 的 `paper-lookup` 备用能力并记录降级原因。
- 依据 DOI 优先、题名与年份辅助的规则合并中英文候选；不同语种不会仅凭译名自动合并。
- 通过已登录浏览器精筛 CNKI，并仅在用户已有权限下下载全文。
- 使用 PDF 全文核验研究方法、应用场景、结论和局限。
- 支持 GB/T 7714、BibTeX、RIS 以及 Zotero 交接。

## 安装

### Windows PowerShell

```powershell
git clone https://github.com/cuijerdaye-hub/cnki-research-workflow.git
Copy-Item -Recurse -Force `
  ".\cnki-research-workflow\skills\cnki-research-workflow" `
  "$env:USERPROFILE\.codex\skills\cnki-research-workflow"
```

如需完整英文多数据库检索，请另行安装 [`O0000-code/paper-search-pro`](https://github.com/O0000-code/paper-search-pro)。本仓库只做编排，不复制或捆绑其代码。安装后新建一个 Codex 任务，让技能被重新发现。

## 前置条件

中文基础检索依赖 [`ExquisiteCore/CNKI-search`](https://github.com/ExquisiteCore/CNKI-search) 提供的 `cnki` 命令行工具：

```powershell
cnki --version
```

英文检索建议配置 OpenAlex API key，以及可选的 Semantic Scholar、Crossref 或 NCBI 联系信息。没有密钥时仍可尝试公开额度；若遇到 `429`、配置缺失或持续零结果，工作流会改走备用来源并在结果中标明。

## 使用示例

```text
使用 $cnki-research-workflow 检索“电力设计院项目集协同管理”，
分别制定中英文检索式，收集中英文期刊文章，统一去重后按章节主题输出。
```

```text
使用 $cnki-research-workflow 查找近十年项目组合治理、跨项目协同、
工程设计组织与数字化协作方面的中英文研究，并核验 DOI 和来源层级。
```

## 工作流

1. 明确章节主题、研究对象、方法、场景、年份和来源层次。
2. 分开构造中文检索式与自然英文检索式，并制定同义词和扩展词。
3. CNKI 串行、小批量检索；英文数据库按接口规则检索并记录来源。
4. 使用 `merge_bilingual_candidates.py` 统一字段、保留来源轨迹并去重。
5. 对候选短名单使用浏览器或全文工具复核，不批量绕过访问控制。
6. 核验 DOI、期刊信息、研究方法、应用场景、结论与局限。
7. 生成参考文献，或导出给 Zotero。

合并示例：

```powershell
python .\skills\cnki-research-workflow\scripts\merge_bilingual_candidates.py `
  --cnki .\cnki-results.json `
  --english .\english-results.json `
  --output .\bilingual-literature.json `
  --csv .\bilingual-literature.csv
```

## 安全边界

- 不破解验证码，不绕过登录、机构权限、付费墙或数据库访问限制。
- 不读取或导出 Cookie、密码、浏览器存储和机构凭证。
- CNKI 请求保持串行、小批量、按需执行。
- 不自动抓取 Google Scholar；英文检索优先使用有正式接口的数据源。
- 同类页面、下载或接口连续失败三次后停止，并报告失败类型和备用路径。
- 搜索元数据、详情页证据和全文证据必须明确区分。

## 仓库结构

```text
.codex-plugin/plugin.json
skills/cnki-research-workflow/
  SKILL.md
  agents/openai.yaml
  references/
    english-routing.md
    quality-safety.md
    routing.md
  scripts/
    merge_candidates.py
    merge_bilingual_candidates.py
```

## 许可证

本仓库原创内容采用 MIT License。第三方项目未被复制或捆绑，相关设计来源和许可证边界见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
