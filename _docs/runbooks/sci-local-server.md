---
docType: runbook
scope: module
status: current
authoritative: true
owner: unstructure
language: zh-CN
whenToUse: "从本机继续 SCI 工作，读取 141 审计证据，或操作服务器与 NAS 前。"
whenToUpdate: "执行端、项目路径、NAS 映射、证据位置或交接方式变化时。"
checkPaths:
  - SCI_DOCUMENT_WORKLOG.md
  - src/journals/**
  - _docs/runbooks/sci-local-server.md
lastReviewedAt: "2026-10-29"
lastReviewedCommit: "e44b06423dff8d5c005c84516704f2e24e9afbac"
---

# SCI 本机与 141 操作说明

后续工作由本机发起，问题、决策和修改记录统一写入仓库根目录的
[SCI_DOCUMENT_WORKLOG.md](../../SCI_DOCUMENT_WORKLOG.md)。本文件只记录执行环境与交接方法。
以下路径于 **2026-10-11（北京时间）只读核实**，不是跨机器通用默认值。

## 2026-10-24 本机整理与历史边界

本机仓库现位于 `/Users/jing/projects/ai-workspace/unstructure`。下文环境、源文件指纹、认证、远端文件存在性均是 **2026-10-11 历史观察**，未在本次重新连接服务器核实。
日记包含 10 月 12 日后续记录，证据本机副本已扩展到 116 个文件，详见 [历史证据索引](../reference/sci-evidence-index.md)。
历史项目名、路径、版本和原始 hash 保留，不能因本地目录改名而推断远端也改名。
本次授权仅允许本机整理及 GitHub 交付；下面的 SSH、证据复制和 API 复核步骤均未执行，也不是本次待办。
后续经用户任务授权确需操作相应环境时，才使用交接检查，并重新确认实际路径、版本和服务状态。
历史“不 commit”已被 2026-10-24 文档交付授权取代；不改变任何历史业务处置的事实与范围。

## 环境与职责（2026-10-11 快照）

| 位置 | 已核实信息 | 适合执行的工作 |
| --- | --- | --- |
| 本机 Mac | 工作区 `/Users/jing/projects/ai-workspace`；本仓库 `/Users/jing/projects/ai-workspace/TianGong-AI-Unstructure` | 任务组织、日记维护、代码开发、评审、Git 交付；不依赖 NAS 的查询可在此运行 |
| 141 服务器 | IP `192.168.1.141`；SSH 别名 `141-bistu-dell-local`；登录用户 `david`；主机名 `dell-ubuntu` | 查阅已有审计与历史日志、核实 NAS 文件、执行必须访问服务器数据的任务 |
| 141 项目 | `/home/david/projects/TianGong-AI-Unstructure` | 原审计和现场 SCI 客户端工作区；操作前检查脏文件 |
| 141 相邻服务仓库 | 日记记载 `/home/david/projects/TianGong-AI-Unstructure-Serve` | 服务实现另归 Unstructure-Serve；本轮未核实其运行实例与部署版本，不从路径推断服务健康 |
| NAS 客户端 | 存在 `/opt/Synology/SynologyDrive`、`/home/david/.SynologyDrive` 与 `/home/david/SynologyDrive` | 仅证明安装/配置目录存在；本轮未确认进程、同步方向、延迟、冲突文件或 NAS 备份健康 |

SSH 别名属于本机配置；在其他机器使用前检查其解析，不能假定已配置。
服务器可达不代表解析服务、队列或 NAS 同步可用。

## 数据与证据路径

下表中的相对路径均相对于 **141 项目根目录**。

| 入口 | 真实位置或边界 |
| --- | --- |
| `docs` | 符号链接到 `/home/david/SynologyDrive/docs/` |
| `processed_docs` | 符号链接到 `/home/david/SynologyDrive/docs/processed_docs/` |
| `docs/journals/` | SCI 原始 PDF |
| `processed_docs/journal_pickle_queue/`、`journal_pickle_with_ref/`、`journal_new_pickle/`、`journal_pickle/` | 四套 PKL 目录，数量与质量以日记的带日期审计为准 |
| `analysis/sci_audit_20261010/` | 10 月 10 日基线；本轮 `du -sh` 约 4.3 GiB，不作为新的文件盘点 |
| `analysis/sci_changes_20261011/` | 后续变更证据与查询脚本；本轮约 432 KiB |

`docs/processed_docs` 与 `processed_docs` 指向同一数据，不能当作两份副本重复处理。
17:24 接手时本机没有 `analysis/`、`docs`、`processed_docs`；本机链接打不开不等于服务器数据不存在。
日记中的 37 个 `analysis/...` 链接本轮在 141 全部检查存在，**未重新验证其内容、统计或业务结论**。
需要证据时先通过 SSH 读取具体文件；确需本机处理时只复制本次所需文件，记录来源与 hash。
不要默认复制整个 4.3 GiB 审计，更不要将 PDF、PKL、原始盘点或密钥提交到 Git。
这些审计目录未跟踪，当前服务器外备份未验证；存在性和 hash 不能代替备份。

## 两端版本快照与单一写入端

接手前日记两端 SHA-256 均为：
`2f6c2120f42ede0e2beba3ad393f72cd5ef90bf9703e900bb191fc6b1a4faad5`。

| 2026-10-11 接手时 | 本机 | 141 |
| --- | --- | --- |
| HEAD | `c4d0aa3a28836d0a5425ec1c538ff295d3aa6c67` | `fefe93a69296ccb9c43e9a6d4643f3324b11a126` |
| 原分支 | `main` | `main` |
| 日记 | 未跟踪；用户要求不要 commit，当前保留工作区文件 | 未跟踪；保留接手时副本 |
| `AGENTS.md` | 已跟踪的完整仓库治理入口 | 未跟踪的 SCI 专用短约定 |
| 其他现场差异 | 本轮未改产品代码 | `src/journals/two_stage_with_ref.py` 已有未提交修改；`analysis/`、`DCU_GPUSTACK_INFRA_BASELINE.md` 未跟踪 |

两端版本不同，且服务器 HEAD 不在本机当前对象库中；本轮**未证明提交先后或分叉关系**。
`two_stage_with_ref.py` 在本机接手版本不存在，在 141 存在且已修改。
日记第 2.3 节的“当前客户端”指原审计所在的服务器工作区，不代表本机或已提交版本。
PIPE-03 的“代码已修改”也必须在实际运行版本上验证，不能沿用到本机结论。

从本次交接起，**本机日记是唯一活动写入端**；141 保留审计和运行现场，不自动同步这次文档修改。
若后续需从服务器直接续写，先完成以下交接：

1. 比较两端日记、AGENTS、HEAD、分支和 `git status --short`；保留双方新增日记和未提交代码。
2. 先把差异保存为可恢复副本或提交，再审阅合并；不要在脏服务器上直接 `pull`、重置、整目录覆盖或用本机 AGENTS 覆盖现场文件。
3. 以本机已跟踪的仓库 AGENTS 为治理基础，保留 SCI 约定。记录同步文件清单、方向、目标 hash、执行时间和新的活动写入端。
4. 同步后重新读取并核对 hash，之后只在新写入端追加；另一端作为副本。日记同步与代码部署分开记录。

这不是仓库双向自动同步方案。NAS 客户端也不负责替代 Git 工作区交接。

## 后续获准远程任务的最小检查

仅在后续任务允许访问服务器时，从本机执行以下只读命令，核对输出与该任务范围。2026-10-24 整理任务不执行：

```sh
ssh -o BatchMode=yes -o ConnectTimeout=8 141-bistu-dell-local 'hostname; cd /home/david/projects/TianGong-AI-Unstructure && pwd && git branch --show-current && git rev-parse HEAD && git status --short && sha256sum SCI_DOCUMENT_WORKLOG.md AGENTS.md && readlink -f docs && readlink -f processed_docs'
```

然后核实本次脚本是否存在、脚本内容及文件 hash、配置变量名、服务入口、目标输入和输出。
依赖 NAS 的写入/清理/重拆前核实同步方向、健康、冲突和可恢复副本；小批次验证后才扩展清单。
任务清单注明论文 ID、版本、路径、运行批次；同一清单避免两端并行写入。
旧 PM2、7770、Redis 状态只属于历史观测，不能据此直接启动、停止进程或恢复全量作业。

## 2026-10-11 本机凭据与入口复核记录

原日记 17:09 指定的配置文件是本机
`/Users/jing/projects/ai-workspace/tiangong-ai-edge-function/.env`，所需变量名为 `X_API_KEY`。
17:24 接手时仅确认文件存在；17:33 已完成本机认证和入口复核，详见下述补充。

`PDF-01` / `LINK-04` 的限定入口复核已于 17:33 完成；未来重核仍先运行已存在论文对照。
查询脚本位于 141 的 `analysis/sci_changes_20261011/check_pdf01_sci_search.py`。
优先将已审阅脚本及所需非密钥清单取到本机，检查依赖和输入路径后，用本机配置运行；不以复制整份 `.env` 到服务器为默认方案。
若实际任务必须远程执行，只注入该任务需要的凭据，禁止回显或写入日记、证据与提交。
此前 401 是认证失败，不是检索零命中。17:33 新结果已解决本机入口认证，但未修复 252 个坏输入。

## 本轮来源指纹

以下是 141 文件在 2026-10-11 接手时的 SHA-256，仅用于定位当时版本，不代表业务验收通过：

| 相对路径 | SHA-256 |
| --- | --- |
| `AGENTS.md` | `e47689d450315cda94b09be350097771644f6bed3b79a6e027a72e7155c247ca` |
| `src/journals/two_stage_with_ref.py` | `17455e77bae2e8be1d65f21307e9472e797c432d094606b5b034281f61356564` |
| `analysis/sci_audit_20261010/reconciliation_summary.json` | `0078921a41163ac0d1bd0f284a6d50f09560082b7fa67ddd19ebef51f5e38ced` |
| `analysis/sci_audit_20261010/quality_summary.json` | `8c2c7cbf59743d1de79e1453cac0f2001eaab0e05b37b82ca4887b04143f194d` |
| `analysis/sci_audit_20261010/validation.json` | `3338ec134b82b8891101ee0b187dd3fcbd12d2647664364cefbe79eadbe8f9f9` |
| `analysis/sci_changes_20261011/check_pdf01_sci_search.py` | `175ce743a37638281137f7a8163305438f89583b7b65a8968ab6896bf4aa1a02` |

未来测量另记日期和新 hash，不覆盖本表。脚本有未提交修改时，单独记录 HEAD 不足以复现运行。

## 2026-10-11 17:33 本机复核后的环境补充

本机已仅复制 `analysis/sci_changes_20261011/check_pdf01_sci_search.py`、同目录 `pdf01_status_verification.json` 和 `analysis/sci_audit_20261010/pdf_input_issues_with_metadata.csv`；新增本机入口响应、混合对照、252 ID 清单与指纹见日记第 6.1 节。其他原审计文件仍需到 141 读取，不把这份少量副本当作完整 4.3 GiB 审计备份。

本机 X_API_KEY 已通过此次请求验证，对照和集合请求均 HTTP 200；密钥未传到服务器。查询结论及时间边界以日记为准，不把此次认证成功当作未来永久有效。日记和新证据未同步服务器，用户要求不 commit；NAS 路径、同步健康和产品运行状态没有因此获得新验证。


## 2026-10-29 SCI 独立进程

142项目仍为 `/home/dell/projects/TianGong-AI-Unstructure`，NAS文档根为
`/home/dell/SynologyDrive/docs`。SCI采用独立源码快照和PM2配置
`ecosystem.sci_parse_worker.json`，进程名 `sci-parse-submitter`、
`sci-parse-finalizer`；只启这两个进程，不启动旧KB生态配置。新进程依赖
database#41的private任务表与SCI队列，部署前先验证迁移和实际数据库角色。
140原two_stage解析服务/Celery保持共享；SCI接收端只发布三个无向量文件，
详情见[开发说明](development.md)。这不是旧THU链路的解析模式开关。
