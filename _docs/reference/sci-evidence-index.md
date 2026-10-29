---
docType: reference
scope: module
status: current
authoritative: false
owner: unstructure
language: zh-CN
whenToUse: "定位 SCI 工作日记引用的历史证据，或决定哪些材料可以提交时。"
whenToUpdate: "证据副本、保留位置、可用性或正式文档的发布边界变化时。"
checkPaths:
  - SCI_DOCUMENT_WORKLOG.md
  - .gitignore
  - _docs/runbooks/sci-local-server.md
  - _docs/reference/sci-evidence-index.md
lastReviewedAt: "2026-10-29"
lastReviewedCommit: "0b223c8ec7ad183b0cd06d55a4e41fc4941aa852"
---

# SCI 历史证据索引

本索引服务于 [SCI 工作日记](../../SCI_DOCUMENT_WORKLOG.md) 和
[本机/141 交接说明](../runbooks/sci-local-server.md)，只说明材料身份与位置。
2026-10-24 仅核对本机文件，未连接服务器、NAS、数据库、业务 API 或索引。
不将历史设计、运行快照或清理记录当作现行配置、业务验收或再次执行授权。

## 正式文档与保留材料

| 材料 | 处理方式 |
| --- | --- |
| SCI 日记、工作约定、交接说明、本文、文档索引与治理配置 | 审阅后纳入 Git；保留带日期的结论及事实边界 |
| `analysis/architecture_20261011/KNOWLEDGE_PIPELINE_DESIGN.md` | 历史多库流水线提案；保留本机，不作为已批准架构提交 |
| `analysis/architecture_20261012/SCI_CLUSTER_DESIGN.md` | 历史集群/传输提案；保留本机，实施需独立任务和新证据 |
| `analysis/course_chain_audit_20261011/COURSE_CHAIN_AUDIT.md` | 10/11 现场、10/12 归档的核查报告；不代表今天的部署状态 |
| 原始 API 回包、数据库/文件清单、环境快照、SQL/Python 操作脚本、截图和复核输出 | 原位保留在 Git 排除的 `analysis/`；本次不执行、不上传 |

这些材料不是待提交的业务代码。`.gitignore` 使用根目录 `/analysis/` 规则；
不要用 `git add -f` 绕过它。若以后要把某段脚本产品化或采纳某份设计，
应单独审阅、移入正式源文件/文档位置并履行对应开发交付。
不把整个证据目录纳入 Git 来“修复”历史链接。

## 本机材料清单（2026-10-24）

根目录为 `/Users/jing/projects/ai-workspace/unstructure/analysis`。
以下包括此前已被 `*.csv`、`*.txt` 等规则忽略的文件；文件没有移动或重写。

| 目录 | 文件数 | 字节数 | 性质与来源限制 |
| --- | ---: | ---: | --- |
| `sci_audit_20261010` | 1 | 134655 | 仅取回的 PDF 异常清单；不是完整原审计 |
| `sci_changes_20261011` | 32 | 7477017 | 当日状态/入口复核、PDF-01 处置、PDF-02 检查；含原始响应及操作脚本 |
| `sci_changes_20261012` | 30 | 1384041 | PDF-03 内容对比、渲染和限定处置记录 |
| `architecture_20261011` | 9 | 103195 | 多库提案及当时环境摘录 |
| `architecture_20261012` | 14 | 96793 | 集群提案、估算与当时环境摘录 |
| `course_chain_audit_20261011` | 30 | 263820 | course 链路核查与历史现场材料 |
| **合计** | **116** | **9459521** | 只证明本机副本的保留范围，不证明业务现状 |

## 历史路径的解析方式

日记的“历史定位”保留原标签和路径，但不提供 GitHub 文件链接。
其中 75 个唯一 `analysis/...` 定位包含文件与目录：本次本机存在 42 个、缺少 33 个。
缺少的 33 个仅能沿用原日记的远端来源，**未在本次核实远端是否仍存在**；
本机不存在不等于证据丢失，也不能冒称已完成新的远端验收。

- 历史 141 根目录：`/home/david/projects/TianGong-AI-Unstructure`。10/11 曾核对 37 个证据路径存在，只是当时存在性检查。
- `analysis/sci_audit_20261010/` 当时约 4.3 GiB，完整内容仍未取回；本次不拉取。
- `src/journals/two_stage_with_ref.py` 是当时 141 的现场未提交脚本，本机基线没有该文件；源码指纹见交接说明。
- 日记中的个人 `tiangong-document-reset` skill 路径是当时本机入口，不随本仓库分发，不保证他人机器可用。
- 历史 `TianGong-AI-Unstructure` 与 `tiangong-ai-edge-function` 本机路径保留作为来源记录；当前工作区目录分别为 `unstructure` 与 `edge-functions`，不据此自动改写远端路径。

需要复核时先确定具体问题与证据日期，按本机清单选择文件；涉及远端时遵守用户当次范围和交接说明。
不得为了补齐链接擅自运行查询/清理脚本、整库扫描或下载整个审计目录。

## 整理前副本与完整性

本机保留目录（不随 Git 分发）：
`/Users/jing/projects/local-evidence/unstructure/issue-43-20261024`。

- `before/`：8 个整理前文档/配置文件和全部 116 个本机证据文件，按原相对路径保存。
- `manifest.json`：这 124 个文件的路径、字节数和 SHA-256；逐文件清单只留本机。
- `historical-locators.json`：上述 75 个历史定位的本机存在性与可计算文件指纹。

整理前清单 SHA-256：`6bb09ae8b9b1749cf71bbd00ace838a672ba9a96866a7921e6e323d824394df0`。

保留性检查须逐字节比较原证据，并对日记审计第 1–3 节、21 项台账和所有既有日记做比较；
唯一允许的历史正文变化是把不可随仓库访问的链接转为保留标签/路径的文字定位。
这是同一台 Mac 上的可恢复副本，**不是异机备份、完整服务器审计副本或灾难恢复证明**。
后续归档迁移必须先验证复制，再更新定位；不能因 Git 已忽略便删除本地唯一证据。

## #43 完成边界

#43 交付的是可维护的文档入口与历史证据边界。正式提交不携带原始证据，不修改产品代码；
数据问题沿用 10/12 的 21 项状态（4 关闭、17 未关闭），本次没有重新验收或关闭其中任何一项。
验证、PR/CI、工作区集成和权限阻塞以 [#43](https://github.com/tiangong-ai/unstructure/issues/43) 的最新记录为准。
