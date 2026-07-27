# CNKI Research Workflow for Codex

面向 Codex 的中国知网端到端研究工作流，覆盖小批量检索、候选去重、浏览器精筛、授权全文下载、PDF 相关性核验、参考文献校验和 Zotero 交接。

## 核心能力

- 使用本机 `cnki` CLI 完成结构化、小批量初筛。
- 在确有需要时使用 Codex 原生 Chrome 控制处理登录态页面。
- 支持 CSSCI、北大核心、CSCD、EI 等来源层次核验。
- 仅通过用户已有权限下载 PDF/CAJ，不绕过登录、验证码或付费墙。
- 使用 PDF 能力核验研究方法、应用场景、结论与局限。
- 校正学位论文类型、网络首发日期和缺失卷期页码等引用问题。
- 可选输出 GB/T 7714、BibTeX、RIS，或交接到 Zotero。

## 安装

### Windows PowerShell

```powershell
git clone https://github.com/cuijerdaye-hub/cnki-research-workflow.git
Copy-Item -Recurse -Force `
  ".\cnki-research-workflow\skills\cnki-research-workflow" `
  "$env:USERPROFILE\.codex\skills\cnki-research-workflow"
```

安装后请新建一个 Codex 任务，使 Skill 被重新发现。

## 前置条件

基础检索依赖 [`ExquisiteCore/CNKI-search`](https://github.com/ExquisiteCore/CNKI-search) 提供的 `cnki` 命令行工具：

```powershell
cnki --version
```

如果命令不存在，请从其 GitHub Releases 安装适合当前系统的版本。Chrome、PDF、引用校验和 Zotero 能力均为按需可选项。

## 使用示例

```text
使用 $cnki-research-workflow 检索“电力设计院项目集协同管理”，
先生成候选清单，再精筛并整理 GB/T 7714 参考文献。
```

```text
使用 $cnki-research-workflow 查找近五年 CSSCI 或北大核心中的相关研究，
只下载有权限的候选 PDF，并按主参考、辅助参考和背景材料分类。
```

## 工作流

1. 明确主题、方法、场景、年份和来源层次。
2. 使用 HTTP CLI 串行检索，每次默认 10–30 条。
3. 在本地合并、去重和筛选候选清单。
4. 仅对短名单使用已登录 Chrome 复核。
5. 仅下载用户已有权限的全文。
6. 阅读全文后判断方法和场景是否匹配。
7. 核对元数据并生成参考文献或导入 Zotero。

## 安全边界

- 不破解验证码，不绕过登录、机构权限或付费墙。
- 不读取或导出 Cookie、密码、浏览器存储和机构凭证。
- 所有 CNKI 请求串行、小批量、按需执行。
- 同类页面或下载连续失败三次后停止。
- 搜索元数据、详情页证据和全文证据必须明确区分。

## 仓库结构

```text
.codex-plugin/plugin.json
skills/cnki-research-workflow/
  SKILL.md
  agents/openai.yaml
  references/
  scripts/merge_candidates.py
```

## 许可证

本仓库原创内容采用 MIT License。第三方项目未被复制或捆绑，相关设计来源和许可证边界见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。
