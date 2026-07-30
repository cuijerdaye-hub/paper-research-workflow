# 英文文献检索路由

## 首选路径

加载 `$paper-search-pro`，由本工作流驱动时优先调用其 headless `agent_search`。运行前读取该 Skill 的 `references/agent_mode.md` 和 `references/setup.md`，并遵守以下规则：

1. 从用户工作目录运行，不进入 Skill 安装目录。
2. 把中文主题转写成独立的英文检索式；`--lang en` 不会自动翻译。
3. 保持 `--min-relevance 0`，再由 Codex 按题名、摘要、方法和场景进行语义评分。
4. 使用多个概念组合迭代检索；单次结果只是一轮探测。
5. 对拟引用记录使用 `--verify-refs` 或 `$citation-management` 复核。

推荐的结构化调用：

```powershell
$env:PYTHONPATH = "$env:USERPROFILE\.codex\skills\paper-search-pro"
python -m scripts.agent_search "<English query>" `
  --lang en --verify --min-relevance 0 `
  --year-min <year> --limit <count> > english.json
```

## 来源选择

| 场景 | 首选来源 | 补充来源 |
|---|---|---|
| 工程管理、社会科学 | OpenAlex | Crossref 核验 DOI；Semantic Scholar 查引文 |
| 计算机、人工智能 | Semantic Scholar（有 API Key 时） | OpenAlex、arXiv |
| 医学、临床 | OpenAlex | PubMed/MeSH、Crossref |
| 已知 DOI 或题名 | `--verify-refs` | `$citation-management` |

`paper-search-pro` 的启发式相关性是候选排序，不是证据等级。经典文献可能因缺摘要被低估；中文查询的启发式分词也较弱，必须由 Codex重新判断。

## 降级规则

出现以下情况时停止该来源并记录原因：

- `paper-search-pro` 未安装或依赖缺失。
- OpenAlex/Semantic Scholar 配置缺失、429、配额不足或零命中。
- 输出不是 `ok: true` 的结构化 JSON。

随后加载 `$paper-lookup`，使用当前可用的 OpenAlex、Crossref、Semantic Scholar、CORE 或 Unpaywall 能力完成候选发现与核验。降级报告必须写明实际使用的数据库、缺少的层次和恢复方法；不得把降级结果标作完整的 `paper-search-pro` 检索。

## 双语合并

- 中文和英文分别保存原始 JSON 与查询日志。
- 英文按 DOI 优先去重；无 DOI 时按题名 + 年份。
- 中文按题名 + 年份；卷期页码缺失时保持“待核验”。
- 不按标题翻译相似度自动合并跨语种记录；只有 DOI 一致时合并。
- 最终记录保留 `origins`、`metadata_status` 和 `fulltext_status`。
