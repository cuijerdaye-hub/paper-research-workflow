# 能力路由与来源边界

## 路由表

| 用户目标 | 首选能力 | 升级条件 |
|---|---|---|
| 主题、作者、年份、文献类型检索 | `$cnki-search` / `cnki` CLI | CLI 被拦截，或需要页面限定条件 |
| 英文主题检索、批量候选与饱和度 | `$paper-search-pro` headless `agent_search` | 配置缺失、限流、零命中或需要替代数据库 |
| 英文降级发现与 DOI 核验 | `$paper-lookup` | 拟正式引用时再用 `$citation-management` 交叉核验 |
| GB/T 7714 初稿 | `cnki --format=citation` | 终稿必须进入元数据核验 |
| CSSCI、北大核心、CSCD、EI | `$chrome:control-chrome` | 页面筛选无法稳定完成时停止 |
| 论文摘要、关键词、基金、机构 | CLI 详情；失败后 Chrome | 只处理短名单 |
| 期刊检索、收录、影响因子、刊期目录 | Chrome | 以页面当时显示值为准并记录日期 |
| PDF/CAJ 下载 | Chrome 中的合法下载入口 | 登录、权限或验证码出现时暂停 |
| PDF 全文相关性核验 | `$pdf:pdf` | CAJ 无法可靠读取时明确报告 |
| DOI、BibTeX 校验 | `$citation-management` | 中文无 DOI 文献以知网详情为主 |
| Zotero 导入 | `$cli-anything-zotero` | 需要 Zotero Local API |

## 分层原则

1. CLI 负责广覆盖和结构化元数据，默认 10–30 条。
2. 本地清单负责去重、排序和候选状态，不重复访问知网。
3. Chrome 负责登录态页面、来源筛选、期刊信息和授权下载。
4. PDF 负责方法、场景、变量、结论和局限的全文证据。
5. 引用工具负责格式与 DOI 一致性，不能补造缺失信息。
6. 中英文检索式分开执行；统一清单只在本地合并，不跨语种猜测同一性。

## 英文路径

1. 用英文概念块调用 `$paper-search-pro`；由编排 Skill 调用时使用 `agent_search` JSON 通道。
2. 保留 OpenAlex/Semantic Scholar/Crossref 等来源标识、查询式、计数、限流和错误信息。
3. 将启发式相关性视为候选排序；Codex 依据题名、摘要、理论、方法和场景重新分级。
4. 对进入正文的候选执行 DOI/题名存在性核验。
5. 如果多源运行失败，加载 `$paper-lookup` 降级，并明确覆盖差异。

详见 [english-routing.md](english-routing.md)。

## 会话交接

知网详情 URL 可能包含会话参数。CLI 与 Chrome 之间传递以下稳定字段：题名、作者、年份、来源和 DOI（如有）。不要依赖跨会话详情 URL；在浏览器中用稳定字段重新定位。

## 第三方方案的处理

### ExquisiteCore/CNKI-search

- 本地已安装的 `cnki` CLI 是快速检索运行时。
- 仓库为 MIT，可在保留许可说明的条件下使用。
- 当前工作流只调用二进制和公开命令，不内嵌其源码。

### cookjohn/cnki-skills

- 提供搜索、筛选、结果解析、详情、下载、导出和期刊导航等任务分类。
- 原仓库面向 Claude Code 的 Chrome DevTools MCP；Codex 中不得照搬工具名。
- 本工作流用 `$chrome:control-chrome` 原生能力重新实现任务编排。
- README 声明 MIT，但源码归档未见独立 LICENSE 文件；不复制其脚本正文。

### LongMarching/cnki-search-skill

- 值得借鉴的概念：workspace/run、结构化错误、批量选择、详情/导出/下载状态。
- 仓库明确未添加开源许可证，保留所有权利。
- 本工作流只原创实现本地候选清单，不复制其代码、字段实现或下载器。

### hansel6666666/cnki-trawl-pick-skill

- 值得借鉴的概念：先筛后下、全文适配判断、3 次失败上限、权限与验证码 STOP 规则。
- 许可证限制修改、再分发和用于其他发布项目。
- 本工作流不内嵌其文件、脚本、选择器或桥接代码。

### O0000-code/paper-search-pro

- 仓库采用 Apache-2.0 License。
- 本工作流只调用用户独立安装的 Skill 和公开命令，不复制其脚本、模板或运行数据。
- 负责英文 OpenAlex/Semantic Scholar/Crossref/PubMed/arXiv 候选发现、结构化去重和存在性核验。
- API Key、配额、缓存和期刊分区数据由 `paper-search-pro` 自身配置管理。

## 工具不可用时

- `cnki` 不可用：报告缺失，并按 `$cnki-search` 的安装说明处理。
- Chrome 不可用：仍可交付 CLI 候选清单，但将来源层次、详情和下载标为待核验。
- PDF 工具不可用：保留下载文件，不声称完成全文核验。
- Zotero 不可用：输出 RIS、BibTeX 或结构化 JSON，由用户后续导入。
- `paper-search-pro` 不可用：加载 `$paper-lookup` 降级；保留错误与实际来源，不声称完成多源或饱和度检索。
