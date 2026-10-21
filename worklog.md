## [2026-10-21] Move lambda/ into infra/lambda/
- **改了什么**：`git mv lambda infra/lambda`；更新 11/15/16/18 部署脚本和 15-rbac-pretoken.py 的打包路径、tools.json 路径，README / infra/README / lambda READMEs、data/ 下 SVG/flow 和本地 docs 的引用
- **为什么改**：Lambda 代码只被 infra 脚本使用，放在 infra/ 下边界更清楚
- **涉及文件/资源**：infra/lambda/**, infra/11-2lo-gateway.sh, 15-rbac-gateway.sh, 15-rbac-pretoken.py, 16-mall-gateway.sh, 18-entra-gateway.sh, README.md, infra/README.md
- **结果**：bash -n / py_compile 通过；所有打包路径存在；没有残留的旧路径；已部署的 Lambda 不受影响

## [2026-10-21] README: cost, teardown reminder and disclaimer
- **改了什么**：README.md 新增「Cost and disclaimer」：会产生费用（约 $0.72/小时）、用完要 teardown（99-teardown.sh + 各 part 的 teardown）、费用和安全由使用者自行负责
- **为什么改**：repo 准备公开，提醒使用者成本和责任
- **涉及文件/资源**：README.md
- **结果**：已推送 GitHub

## [2026-10-21] Mask AWS account ID before making the repo public; IdC prerequisites
- **改了什么**：发布文件中的账号 ID 全部替换为 `123456789012`（14 个文本文件：runbook、SVG、flow HTML、registry JSON 等）；`infra/00-config.sh` 的 `ACCOUNT_ID` 改为用 `aws sts get-caller-identity` 查询；20 张 console 截图用 macOS Vision OCR 定位账号 ID、ARN 和 Isengard 角色并涂黑，右上角账号区域统一涂黑；infra/README.md 加 Prerequisites（需已有 IAM Identity Center，并在 00-config.sh 填 IDC_INSTANCE_ARN / IDENTITY_STORE_ID）
- **为什么改**：用户准备把 GitHub repo 改为 public
- **涉及文件/资源**：infra/00-config.sh, infra/README.md, data/**, RUNBOOK-cognito-idc.md, infra/registry/*.json, tests/results-network.txt
- **结果**：发布文件 grep 无真实账号 ID；OCR 复查截图 0 处命中；00-config.sh 仍解析出真实账号（本地脚本不受影响）

## [2026-10-21] New data/ folder for the assets the repo links to
- **改了什么**：把 RUNBOOK 和脚本引用的 34 个文件从 docs/ 移到 data/（6 张架构 SVG、flow.html / flow-rbac.html 及其 build 源、data-views.*、quick-mcp-connector.md、19 张 console 截图 + manifest、IdC 截图），新增 data/README.md；所有引用 `docs/<file>` 改为 `data/<file>`（RUNBOOK-cognito-idc.md、tests/render_data_views.py 输出目录、本地 decks / email-draft / entra runbook / docs/build_console_shots.py）
- **为什么改**：docs/ 不上 GitHub，runbook 里的图片和链接在 GitHub 上是坏的
- **涉及文件/资源**：data/**, RUNBOOK-cognito-idc.md, tests/render_data_views.py, docs/README.md
- **结果**：发布文件里的相对链接全部能找到目标；`python3 data/build_flow.py` 重建成功；已推送 GitHub

## [2026-10-21] webchat: app.py → obo_app.py; Entra README split out
- **改了什么**：`git mv webchat/app.py webchat/obo_app.py`，更新 14-deploy-webchat.sh（打包列表、`WEBCHAT_APP=obo_app`）、lambda_adapter 注释、runbook；webchat/README.md 的 Entra 内容移到 `webchat/README-entra-id.md`（gitignored）
- **为什么改**：命名与 oauth_app / rbac_app 对齐；Entra 内容只留本地
- **涉及文件/资源**：webchat/obo_app.py, webchat/README.md, webchat/README-entra-id.md, infra/14-deploy-webchat.sh, .gitignore, RUNBOOK-*.md
- **结果**：用 lambda_adapter（WEBCHAT_APP=obo_app）请求 GET / 返回 200；已部署的 Lambda 不受影响（下次跑 14-deploy-webchat.sh 时切到 obo_app）

## [2026-10-21] tests/results/ kept local only
- **改了什么**：`tests/results/` 加入 .gitignore 并 `git rm --cached`；本地文件不动
- **为什么改**：用户要求测试结果不上 GitHub
- **涉及文件/资源**：.gitignore；GitHub serenity0102/agentcore-identity-for-gateway
- **结果**：GitHub tree 中无 tests/results/

## [2026-10-21] Entra ID setup removed from GitHub (kept locally)
- **改了什么**：`agent_entra/`、`RUNBOOK-entra-id.md`、`infra/*entra*`（18/19/20 脚本、policies、registry）、Entra tests 和结果、`tests/totp.py`、`webchat/entra_*` 加入 .gitignore 并 `git rm --cached`；本地文件不动；README 注明 Entra 部分 local only
- **为什么改**：用户要求 GitHub 上不放 Entra ID 相关 setup
- **涉及文件/资源**：.gitignore, README.md；GitHub serenity0102/agentcore-identity-for-gateway
- **结果**：见 GitHub tree 校验（无 entra 文件）

## [2026-10-21] Rename agent/ to agent_obo/
- **改了什么**：`git mv agent agent_obo`（含本地 `.venv`）；33 个文件里的路径引用改为 `agent_obo/`（infra 脚本、tests、webchat、README、两份 runbook，以及本地的 docs/decks）
- **为什么改**：目录名明确对应 OBO agent，和 `agent_oauth/`、`agent_entra/` 对齐
- **涉及文件/资源**：agent_obo/, infra/08,11,14,17,18,19,20, tests/, webchat/, README.md, RUNBOOK-*.md；S3 前缀 `agent/` 和 IAM policy 不变（不影响已部署的 runtime）
- **结果**：bash -n、py_compile 通过；`tests/validate_matrix.py` 16/16；已推送 GitHub

## [2026-10-21] Publish RUNBOOK-entra-id.md without passwords
- **改了什么**：RUNBOOK-entra-id.md 的 Demo access 表格密码列改为指向 `tests/.entra-users.env`；带密码版本另存为 RUNBOOK-entra-id.local.md（gitignored）；README 说明同步更新
- **为什么改**：用户要求把 Entra runbook 推到 GitHub，但不公开测试用户密码
- **涉及文件/资源**：RUNBOOK-entra-id.md, RUNBOOK-entra-id.local.md, .gitignore, README.md
- **结果**：脚本比对 tests/.entra-users.env，确认 RUNBOOK-entra-id.md 中无密码；已推送 GitHub

## [2026-10-21] Entra GUI 网址和账号写进 RUNBOOK-entra-id.md 和三份 deck
- **改了什么**：
  - `RUNBOOK-entra-id.md` 目录之后加了「Demo access」一节，直接显示：Entra demo GUI 和 RBAC GUI 的 Entra 卡片、4 个 Entra 用户和密码、MFA 方法、每个用户的预期结果；
  - 这份 runbook 加入 `.gitignore`（之前从未 commit 过）；
  - 三份 deck 的 accounts 页和 Entra demo 步骤都加上 GUI 路径（由 subagent 完成）。
- **为什么改**：用户要求；密码放进 runbook 的做法由用户选定（runbook 改为 gitignore）。
- **结果**：`git check-ignore` 确认 runbook 已被忽略；`<details>` 30/30 配对。

## [2026-10-20] RUNBOOK-cognito-idc.md 重新排序 part
- **改了什么**：
  - part 顺序改为：Part 1 · Amazon Quick → Gateway、Part 2 · 3LO、Part 3 · 2LO（原 Part 1）、Part 4 · OBO（原 Part 3，含 per-user Gateway RBAC）；目录和架构总览表按新顺序排列；
  - 正文里指向旧构建顺序的「Part N」改成描述性名称或新编号；
  - 更新其他文件的交叉引用（README、tests、Quick 指南、flow、email、三份 deck 的 build 脚本），然后重建三份 deck、两个 flow 页面和 email PDF。
- **为什么改**：用户要求把 Quick → Gateway 放在第一部分。
- **结果**：调整前后逐行对比，没有丢失任何行；`<details>` 60/60 配对；三份 deck 的检查都通过。

## [2026-10-20] Cognito runbook 新增 Part 4：Amazon Quick → rsidc-mall-gateway（由 Quick 做 3LO，不是 OBO）
- **改了什么**：
  - 新增架构图 `docs/architecture-quick-mall.svg`（.tsx 一并保存；skill 里的 scene 是 `rsidc_quick_mall.tsx`）；
  - `RUNBOOK-cognito-idc.md` 新增 Part 4，在目录和架构总览表里加了对应条目。共 7 个可折叠步骤：分类（3LO / OBO 对比）、Quick connector 配置（含 "Signed in as wei@techfinance.example.com"）、AWS 端设置、wei 的 4 个 tool、"No access token" 排错（history/007）、demo 步骤（ds1 部分标记为待记录）、清理。
- **为什么改**：用户要求加上 Quick 访问 mall gateway 的架构，并说明属于 3LO 还是 OBO。
- **结果**：
  - `<details>` 60/60 配对，代码块完整闭合，图片路径都存在；
  - client secret 没有出现在任何文件里；
  - 渲染成 HTML 后，Part 4 的架构图不用展开就能看到，7 个步骤默认收起。

## [2026-10-20] 修复 Amazon Quick MCP connector 拿不到 access token
- **改了什么**：
  - 在 Cognito 新建 resource server，identifier 就是 mall Gateway 的 MCP URL，scope 为 `invoke`；
  - 把这个 scope 加进 `rsidc-quick-mcp` 和 OBO client 的允许 scope（只做增量修改，完整回写配置并比对前后差异）；
  - 把以上写进 `infra/16-mall-cognito.py`，可以重复执行；新增 history/007，更新 Quick 指南。
- **为什么改**：Quick 在 authorize 和 token 请求里都带 RFC 8707 的 `resource` 参数，而 Cognito 只接受已注册的 resource server，否则 token 端点返回 `invalid_grant`。这个结论有 CloudTrail 记录，也自己复现过。
- **结果**：带 `resource` 也能拿到 token，`aud` 为 Gateway URL；Cedar 照常按用户执行（wei 4 个 tool，ds1 2 个，ds1 调用 hourly 被拒）；mall 回归 25/25。

## [2026-10-20] Entra ID demo web GUI (2LO / 3LO / OBO in one page)
- **改了什么**：
  - 新增 `webchat/entra_app.py` 和 `entra_index.html`：Entra 登入（PKCE）和登出（`logout_hint`），以及 2LO、OBO（含 Graph）、3LO（consent → callback → CompleteResourceTokenAuth → Token Vault）三个面板，页面只显示 claims；
  - `infra/14-deploy-webchat.sh` 增加第 4 个 function `entra`，新的 inline policy 是 `infra/policies/webchat-entra-permissions.json`；
  - `18-entra-setup.py` 增加 `WEB_ENTRA_URL` 的 redirect；`20-entra-agentcore.sh` 的 return URL 改成合并，不再覆盖。
- **为什么改**：用户要求和 Cognito/IdC 一样，给 Entra 也做一个前端 GUI，方便 demo。
- **涉及资源**：Lambda `rsidc-webchat-entra`，HTTP API `https://se2shbmsej.execute-api.ap-southeast-1.amazonaws.com`，`rsidc-webchat-role` 上的 inline policy `webchat-entra`，Entra test client 的 redirect URI，Entra workload identity 的 return URL。
- **结果**：
  - 浏览器端到端测试（lo3user）：2LO 拿到 app roles List + Footfall；OBO 的 aud 换成 rsidc-mall-api，保留了 user，lo3user 没有 role 所以是 0 个 tool；3LO 走完 TOKEN_FROM_VAULT 和 Graph /me；登出正常；
  - 回归：4 个 GUI 都返回 200；entra 2lo 7/7、obo 10/10、Part 6 19/19。

## [2026-10-20] Cognito runbook：OBO 和 Gateway RBAC 的架构图直接显示
- **改了什么**：
  - `RUNBOOK-cognito-idc.md` 的 OBO 架构图原本藏在第一个折叠步骤里，现在移到 Part 3 开头直接显示，和 2LO、3LO 一致；
  - Gateway tool RBAC 一节直接显示 `architecture-rbac.svg`（demo 版）和 `architecture-rbac-mall.svg`（客户版），并加上 flow 动画的链接。
- **为什么改**：用户指出 OBO 部分看不到架构图。
- **结果**：`<details>` 53/53 配对，图片路径都存在；不展开任何步骤也能看到 5 张架构图。

## [2026-10-20] RUNBOOK 改名为 RUNBOOK-cognito-idc.md，并重组为 2LO / 3LO / OBO 三部分
- **改了什么**：
  - `git mv RUNBOOK.md RUNBOOK-cognito-idc.md`；结构改为 Shared foundation → Part 1 · 2LO → Part 2 · 3LO → Part 3 · OBO（包括 Gateway tool RBAC）→ Appendix；
  - 每部分开头是一张概览表，列出每一步的名称、用途和结果；每一步放在可折叠的 `<details>` 里，点开才看细节；
  - Entra 相关的 Part 6、6b、7 只留一行指向 `RUNBOOK-entra-id.md` 的链接；
  - `docs/build_console_shots.py` 改为按每一步的 `<details>` anchor 插入截图。顺便修了一个旧问题：Step 9、10 的 Cognito 截图之前错放在 OBO 的 Step 9、10 下面，现在放在 2LO 的对应步骤；
  - 全仓库的引用都更新了（README、infra/README、tests、docs/flow*、email、review、decks、scheduled task），并重建 flow.html、三份 deck 和 email PDF。
- **为什么改**：用户要求 Cognito + IdC 和 Entra 两份 runbook 分开，每份按 2LO、3LO、OBO 组织，并且能一眼看到全部步骤。
- **结果**：
  - 非 Entra 部分的每一行内容都原样搬到了新文件里（逐行覆盖检查，0 缺失）；
  - 53 个 `<details>` 开闭平衡，代码块没有跨块；data-views 和 console-shots 的 marker 都还在；
  - 用 CommonMark 渲染后在浏览器里检查过，可以正常折叠和展开；
  - 三份 deck 的关键字扫描为 0，没有重复的 slide 文件。

## [2026-10-19] 2LO/3LO deck 彻底分开；demo 输入写进 notes；Entra 架构图
- **改了什么**：
  - 2LO deck 里不再有任何 3LO 内容，3LO deck 里不再有任何 2LO 内容：文字、表格、粤语 notes、原图里的 caption（用 `docs/decks/recaption.py` 重画）、截图裁切都处理了；
  - 每张 demo、setup 和 cheat sheet 的 notes 末尾都加了 【Demo 輸入】（URL、用户/密码、点击或命令、预期结果）；
  - 新增三张 Entra ID 架构图：`docs/architecture-entra-{2lo,3lo,obo}.svg`，风格与 Cognito + IdC 版一致，并放进对应的 deck。
- **为什么改**：用户要求 2LO 和 3LO 完全分开，demo 输入放在 notes 里，Entra 也要有和 Cognito/IdC 一样的架构图。
- **涉及文件**：`docs/decks/build_{2lo,3lo,obo}.py`、`docs/decks/fix_layout.py`（跳过 "Scenario:" 开头的页）、`docs/decks/recaption.py`、`docs/decks/img/*`，以及 skill 里的三个 scene `rsidc_entra_{2lo,3lo,obo}.tsx`。
- **结果**：
  - 2LO 46 页、3LO 46 页、OBO 27 页；
  - 另一流程的关键字命中为 0；每份 deck 的 demo 页都有 【Demo 輸入】；没有重复的 slide 文件；
  - 都在 PowerPoint 导出后检查过。

## [2026-10-19] 三份 deck 把 demo 穿插进讲解里，加 demo 步骤和粤语讲稿
- **改了什么**：
  - 2LO、3LO、OBO 三份 deck 的每一页场景 frame 后面，都紧跟一页「Demo · step」：左边是 Cognito + IdC，右边是 Entra ID，每边写清楚要做什么、会看到什么、去哪里看，并配 GUI 截图；
  - 最前面加了 demo 准备页，以及用户名、密码和 URL 页（红色 INTERNAL banner）；
  - 每一页都加了粤语 speaker notes；原来单独的 demo 页移到附录做 cheat sheet；
  - 新增 `tests/entra_demo.py`，用于现场展示 claims，不会打印 token；
  - 修了一个 bug：deck 超过 31 页后，新加的 slide 文件名会和保留的原始 slide 撞名，现在会重新编号。
- **为什么改**：用户要求一边讲原理一边 demo，并要有 demo 步骤（URL、用户、密码）和粤语讲稿；密码按用户要求放在 slide 上。
- **涉及文件**：`docs/decks/build_{2lo,3lo,obo}.py`、`docs/decks/img/*`、`tests/entra_demo.py`、`.gitignore`（三份 deck 都设为不提交）。
- **结果**：2LO 47 页、3LO 45 页、OBO 26 页；每份 deck 的 notes 都覆盖全部页面；没有重复的 zip part；都在 PowerPoint 导出后逐页检查过；原始 deck 没动。

## [2026-10-19] Part 7: Entra ID × AgentCore Identity（2LO / 3LO / OBO）+ 三份 deck
- **改了什么**：
  - Entra：新建 app `rsidc-entra-agent`；
  - AgentCore：新建 credential provider `rsidc-entra`（MicrosoftOauth2，一个 provider 同时用于 2LO、3LO、OBO）和 runtime `rsidc_entra_agent`，加上 `agent_entra/` 和 `tests/entra_identity_tests.py`；
  - 新增三份 deck：`docs/AgentCore-Identity-2LO.pptx`、`-3LO.pptx`、`-OBO.pptx`，以及 `docs/decks/*`、`docs/part7/*`、history/006。
- **为什么改**：用户要求补上 Entra ID 的 2LO、3LO、OBO 场景，并把实现方法写进 deck 的 32–53 页（Cognito + IdC 和 Entra ID 两种做法都要有），分成三份 PPT。
- **涉及资源**：
  - runtime `rsidc_entra_agent`、provider `rsidc-entra`、role `rsidc-entra-runtime-role`；
  - Entra app `rsidc-entra-agent` 和用户 `lo3user`；
  - `rsidc-mall-api` 的 App Roles 增加了 Application（属于增量修改）。
- **结果**：
  - 测试：2LO 7/7、OBO 10/10、3LO 5/5（连跑两次），Part 6 回归 19/19；
  - 三份 deck 都在 PowerPoint 导出后逐页检查过；
  - 遗留问题：Entra Security defaults 强制注册 MFA，wei/ds1/chen 暂时无法交互式登录，要等用户在门户里关掉 Security defaults。

## [2026-10-07] RBAC GUI：Entra ID 登出
- **改了什么**：
  - 加了「Sign out of Entra ID」按钮：先清掉 app 的 session，再调用 Entra 的 `/logout`，带上 `logout_hint` 和已注册的 `post_logout_redirect_uri`（`/entra/signed-out`）；
  - 回到 GUI 后显示「✓ Signed out」；
  - test client 的 ID token 增加了 `login_hint` optional claim，并注册了 signed-out 的 redirect URI。
- **为什么改**：用户要求 Entra 版有登出功能。原来的链接会停在 Entra 的选择账号页面，也回不到 GUI。
- **涉及文件/资源**：`webchat/rbac_app.py`、`rbac_index.html`、`infra/18-entra-setup.py`；Lambda `rsidc-webchat-rbac`；Entra app `rsidc-mall-test-client`。
- **结果**：ds1 登出后回到 GUI 并显示已登出；刷新后要重新登录；没有 session 时 API 返回 401；同一个浏览器里登着 3 个 Entra 账号也不会弹出选择账号。

## [2026-10-07] RBAC GUI 加入 Entra ID 登录
- **改了什么**：`webchat/rbac_app.py` 和 `rbac_index.html` 增加「Sign in with Entra ID」和 Entra 卡片；`infra/18-entra-setup.py` 给 test client 加上 GUI 的 redirect URI；`infra/14-deploy-webchat.sh` 把 ENTRA 相关环境变量传给 Lambda。
- **为什么改**：用户要求把 Entra 版放进同一个 GUI。
- **涉及文件/资源**：Lambda `rsidc-webchat-rbac`；Entra app `rsidc-mall-test-client` 的 redirect URI。
- **结果**：浏览器里用 Entra 的 wei、ds1、chen 登录，分别能用 4、2、0 个 tool；同一个 GUI 上 Cognito 的 ds1 结果不变。

## [2026-10-07] Entra ID 版 tool RBAC（Part 6）
- **改了什么**：
  - 用 `infra/18-entra-setup.py`（Graph）配置 Entra：两个 app、4 个 App Role、wei/ds1/chen 三个用户，以及按用户的 role 分配；
  - 用 `infra/18-entra-gateway.sh` 建了直接信任 Entra 的 Gateway 和单独的 policy engine；
  - 测试脚本 `tests/entra_rbac_tests.py`；新增 `docs/architecture-rbac-entra.svg`，`flow-rbac.html` 加了 Entra 标签页。
- **为什么改**：用户有 Entra tenant，要验证 Entra ID 下的 Gateway RBAC。
- **涉及文件/资源**：
  - Entra：rsidc-mall-api 和 rsidc-mall-test-client 两个 app，以及 3 个用户；
  - AWS：gateway rsidc-mall-entra-gateway、policy engine rsidc_mall_entra_pe，以及 rsidc-mall-gateway-role 上的 inline policy `entra-gateway`。
- **结果**：
  - Entra 测试：LOG_ONLY 15/15、ENFORCE 19/19、权限变更 4/4；
  - Cognito 回归不受影响：mall 25/25、Part 3 12/12、OBO 16/16；
  - Azure 侧只用了免费功能；
  - 踩到的坑：policy 名称在整个 Region 内必须唯一；共用的 role 需要单独加 inline policy；IAM 生效有延迟，需要重试。

## [2026-10-06] 把 runtime 和 gateway 登记到 AWS Agent Registry（Part 5）
- **改了什么**：
  - 在 ap-northeast-1 建了 registry `rsidc-registry`，审批方式是人工审批；
  - 登记了 5 条 record，都已经是 APPROVED：2 个 runtime（CUSTOM 类型）和 3 个 gateway（MCP 类型，含 tool 列表）；
  - 新增 `infra/17-agent-registry.py` 和 `infra/registry/`。
- **为什么改**：用户要求把这些 agent 和 MCP server 放进 Agent Registry，方便发现和治理。
- **涉及文件/资源**：registry `wCf04AFofS2kuI0i`，以及 5 条 record（ID 见 RUNBOOK Part 5）。
- **结果**：
  - 语义搜索能按自然语言找到正确的 record，重跑会全部跳过（幂等）；
  - 限制：Agent Registry 不支持 ap-southeast-1，所以 registry 建在东京，跨 Region 不能自动发现；
  - endpoint 都需要 JWT，没法用 URL 同步，所以 record 是手工建的；
  - 第一次让 subagent 做时，它在 `aws … help` 的分页器上卡住了。

## [2026-10-06] Tool RBAC web GUI（API Gateway → Lambda）+ 架构图和 flow 更新
- **改了什么**：
  - 新增 `webchat/rbac_app.py` 和 `rbac_index.html`（第三个 GUI），`infra/14-deploy-webchat.sh` 增加 `rbac` 这个 function；
  - `docs/architecture-rbac.svg` 加入 GUI（API Gateway → Lambda），并去掉了起点画错的 JWKS 箭头（它画在 Policy 上，实际校验 JWT 的是 Gateway）；
  - 新增客户版架构图 `docs/architecture-rbac-mall.svg`（Quick 和 GUI → Gateway → mall tools，Cognito group 映射）；
  - `docs/flow-rbac.html` 改为两个标签页（demo 和客户版），由 `docs/flow-rbac.config.mjs` 生成。
- **为什么改**：用户要像 OBO demo 一样，有一个可以在浏览器里操作的 RBAC GUI，并同步更新架构图和 flow。
- **涉及文件/资源**：Lambda `rsidc-webchat-rbac`，HTTP API `80l9l7cdk2`，Cognito OBO client 新增 callback 和 logout URL。
- **结果**：wei、ds1、chen 在浏览器里的结果都符合预期（见 RUNBOOK Step 14b）。flow 两个标签页都能从头放到尾，没有 JS 错误。修复了页面同时发出两个请求、在并发 1 下被限流（429）的问题。

## [2026-10-06] Part 4：客户版（Amazon Quick → AgentCore Gateway(MCP) → Lambda tools），权限映射放在 Cognito group
- **改了什么**：
  - 新建 Gateway `rsidc-mall-gateway-skatnrktwr`，它本身就是 MCP server；一个 Lambda target `mall` 提供客户的 4 个 tool
  - Policy Engine `rsidc_mall_pe-njxtj4u_wi`（ENFORCE），每个 tool 一条固定的 Cedar 规则
  - Cognito groups `mall-analyst` / `mall-viewer`，组的 Description 里写映射
  - 给 Quick 用的 app client `rsidc-quick-mcp`
  - trigger 增加 Cognito group 作为权限来源（`ROLE_SOURCES=cognito,idc`），并改为调用 `live` alias
  - 新增 `docs/quick-mcp-connector.md`、RUNBOOK Part 4、history/005
- **为什么改**：客户的前端是 Amazon Quick，映射用 Cognito group 管理；用户要求用 Gateway 当 MCP server、用 Lambda 做 tool
- **涉及文件/资源**：`infra/16-mall-*`、`lambda/mall_tools/`、`lambda/pretoken/handler.py`、`infra/15-rbac-pretoken.py`、`tests/mall_rbac_tests.py`
- **结果**：LOG_ONLY 15/15、ENFORCE 25/25、change 5/5；回归 Part 3 12/12、OBO 16/16、2LO/3LO 18/18，两个 webchat 都返回 200。部署时发现 trigger 在 `$LATEST` 上被提前更新的问题，已修复（history/005）

## [2026-10-06] Part 3：AgentCore Gateway 按用户限制 tool（Cedar + Entra 风格的 roles claim，映射放在 IdC）
- **改了什么**：
  - 新建 Gateway `rsidc-rbac-gateway-xwjxlwbllu`（入站用 Cognito access token，`allowedClients` = OBO client），后面两个 tool：Lambda `rsidc-tool-sales`（A）和 `rsidc-tool-crm`（B）
  - 新建 Policy Engine `rsidc_rbac_pe-b396yeuocw`，每个 tool 一条固定 Cedar 规则（要求 `roles` 里有 `Tools.X.Read`），先 LOG_ONLY 再 ENFORCE
  - 新增 Cognito Pre Token Generation V2 trigger `rsidc-pretoken-roles`：按 email 查 IdC 组，读组 Description 里的映射，写入 access token 的 `roles`；出错即拒绝登录
  - 新建项目自有的 IdC 组 `rsidc-gw-analyst`（wei）和 `rsidc-gw-viewer`（ds1）
  - 打开 gateway 日志投递
  - 新增脚本 `infra/15-rbac-*`、测试 `tests/rbac_tests.py` 和 `tests/rbac_change_tests.py`
- **为什么改**：回答两个问题：Gateway 能否按用户或角色限制 tool；能否用 IdP 的组实现 RBAC 而不改 MCP server 代码。客户可能用 Entra ID，所以 claim 采用 Entra App Role 格式
- **涉及文件/资源**：见 RUNBOOK Part 3。已有的 IdC 组不是本项目创建的，所以没有改它们的 Description，改用项目自有的组
- **结果**：
  - 测试矩阵：baseline 9/9，LOG_ONLY 12/12，ENFORCE 12/12，只改 IdC 的变更测试 10/10
  - 回归：OBO 16/16，2LO/3LO 18/18，webchat 正常
  - 发现：`tools/list` 自动过滤；被拒的 `tools/call` 返回 HTTP 200 + `isError`；被拒的 JWT 返回 403（不是 401）；已签发的 token 要等过期后才失去权限

## [2026-10-06] 移除 Lambda 内的 IP 白名单
- **改了什么**：从 `webchat/lambda_adapter.py` 删除 `ALLOWED_IPS` 检查，并从 `infra/14-deploy-webchat.sh` 删除 IP 检测和该环境变量
- **为什么改**：用户要求，之后会在 API 外层限制 IP
- **涉及文件/资源**：Lambda `rsidc-webchat-obo`、`rsidc-webchat-oauth`
- **结果**：两个 GUI 返回 200；来源 IP 为 9.9.9.9 的模拟请求也返回 200（说明已不再过滤）。目前只靠 Cognito 登录保护

## [2026-10-06] Web GUI 改为 API Gateway HTTP API → Lambda（去掉 Function URL）
- **改了什么**：`infra/14-deploy-webchat.sh` 改为快速创建 HTTP API（`$default` 路由、payload 2.0），Lambda 资源策略只允许对应 API（`SourceArn`），删除了 Function URL；Cognito callback 和 workload identity return URL 换成 API 地址并清理旧 URL；webchat 角色增加 3LO provider secret 的 `GetSecretValue`
- **为什么改**：Function URL 的 `Principal:*` 被账号安全自动化（`lambda_function_policy_block_public_access`）自动移除，用户要求放在 API Gateway 后面；3LO 绑定在 Lambda 角色下报 AccessDenied
- **涉及文件/资源**：API `604penmkc9`（OBO）、`k9vfijvbu9`（OAuth），Lambda `rsidc-webchat-obo`/`oauth`，`infra/policies/webchat-permissions.json`，`webchat/lambda_adapter.py`
- **结果**：浏览器端到端以 wei 测试：OBO SQL 和自然语言（约 6.2s）、2LO、3LO 强制重新授权都通过；非白名单 IP 返回 403

## [2026-10-06] Web GUI 部署到 AWS（Lambda Function URL，IP 白名单）+ README 加 2LO/3LO/OBO 对比
- **改了什么**：新增 `webchat/lambda_adapter.py`（把 Function URL 事件转成原 http.server handler，按 sourceIp/CIDR 放行）；`app.py`/`oauth_app.py` 的 base URL 改为可配；`oauth_app.py` 改用默认凭证链；新增 `infra/14-deploy-webchat.sh` 和 `infra/policies/webchat-permissions.json`；`13-web-login-client.py` 支持 `WEBCHAT_URLS`；README 加 2LO/3LO/OBO 对比表
- **为什么改**：用户需要在 AWS 上用 GUI；Cognito 的非 localhost 回调必须用 HTTPS，所以 Function URL 是最简单的选择（不用 EC2、证书、ALB）
- **涉及文件/资源**：Lambda `rsidc-webchat-obo`、`rsidc-webchat-oauth`，IAM `rsidc-webchat-role`，Cognito OBO client 的 callback，OAuth workload identity 的 return URL
- **结果**：白名单 IP 访问返回 200（IPv4/IPv6 都通），非白名单返回 403；第一次部署时 IPv6 被拒，已修复

## [2026-10-06] 2LO/3LO 图与动画标注 inbound / outbound 认证边界
- **改了什么**：两张图新增 "Auth boundaries" 表（每个组件的 Inbound / Outbound 认证）；2LO 图新增 Gateway → Cognito 虚线 "inbound JWT check (JWKS)"；图例与 flow.html 的步骤标题、徽章改为明确标注 Runtime INBOUND（Cognito JWT）、Runtime OUTBOUND（AgentCore Identity）、Gateway INBOUND（Cognito JWT，allowedClients=2LO）、Gateway OUTBOUND（IAM role）；3LO 第 7 步标注 Cognito userInfo 自行校验 token；邮件与 RUNBOOK 增加同一说明；PDF 重新生成
- **为什么改**：用户以为 Gateway 用 AgentCore Identity 认证；实际（已用 get-gateway / get-gateway-target / get-agent-runtime 只读核实）Gateway 入站也是 Cognito JWT，AgentCore Identity 只是 runtime 的出站代理
- **涉及文件/资源**：`docs/architecture-2lo.*`、`docs/architecture-3lo.*`、`docs/_codepanel.ts`、`docs/flow_template.html`、`docs/flow.html`、`docs/email-draft.html/.pdf`、`RUNBOOK.md`
- **结果**：两张图目视检查通过；flow.html 三个标签无 JS 报错，2LO 第 5 步显示 JWKS 校验动画

## [2026-10-06] 2LO 与 3LO 拆分为两张独立架构图和两个独立动画
- **改了什么**：新建 `docs/architecture-2lo.svg`（用户登录 → runtime → Identity M2M → Cognito client_credentials → Gateway → Lambda → Redshift svc_reporting，7 步，仅 2LO 代码）和 `docs/architecture-3lo.svg`（GUI 8081 → Cognito LOGIN 1/2 → runtime → Identity USER_FEDERATION → AgentCore callback → CompleteResourceTokenAuth → Token Vault → userInfo，7 步，仅 3LO 代码）；删除旧的合并图 `architecture-2lo-3lo.*`；flow.html 的 2LO / 3LO 标签各自绑定自己的图、节点、连线与每步代码；邮件第 5 节和 RUNBOOK Part 2 改为两张图；修复代码面板按列排布时背景高度计算错误（codePanel 未传 columnMajor）
- **为什么改**：避免 2LO 与 3LO 的组件和代码混在一起，便于分别理解
- **涉及文件/资源**：`docs/architecture-2lo.*`、`docs/architecture-3lo.*`、`docs/_codepanel.ts`、`docs/flow_template.html`、`docs/build_flow.py`、`docs/flow.html`、`docs/email-draft.html/.pdf`、`RUNBOOK.md`、`docs/README.md`
- **结果**：两张图目视检查通过；flow.html 三个标签（OBO 8 步 / 2LO 7 步 / 3LO 7 步）全部跑通无 JS 报错；邮件 PDF 28 页

## [2026-10-06] 架构图/动画加入 "IdC 信任 Cognito" 与关键 token 代码
- **改了什么**：OBO 架构图新增 Cognito → IdC 虚线 "IdC trusts Cognito JWTs (TTI · JWKS)"，步骤 4 说明 TTI 校验；两张架构图底部新增 "Key token code" 代码面板（OBO：PKCE code→id_token、Bearer 调 runtime、create-trusted-token-issuer、CreateTokenWithIAM、IdpTokenAuthPlugin；2LO：GetResourceOauth2Token(M2M)、Gateway tools/call、Data API svc_reporting；3LO：USER_FEDERATION、CompleteResourceTokenAuth、vault token + 身份校验）；flow.html 每一步显示对应代码，OBO 第 4 步增加 IdC↔Cognito JWKS 动画；邮件 PDF 重新生成
- **为什么改**：让读者看清 OBO 依赖的信任关系，以及三种模式里获取/交换 token 的实际代码
- **涉及文件/资源**：`docs/architecture.svg/.tsx`、`docs/architecture-2lo-3lo.svg/.tsx`、`docs/_codepanel.ts`、`docs/flow_template.html`、`docs/flow.html`、`docs/email-draft.pdf`
- **结果**：两张图 headless Chrome 目视检查通过；flow.html 三个标签无 JS 报错，21 个步骤附代码

## [2026-10-05] 新 skill aws-deploy-evidence + 本项目完整 review pack
- **改了什么**：创建 `~/.claude/skills/aws-deploy-evidence/`（SKILL.md、capture.py 只读截图+URL/时间清单+跳转检测、build_review.py 运行只读校验并生成 REVIEW.md/HTML/PDF、cfn/tf inventory 脚本、console-urls.md 含已踩坑点）；并用它为本项目生成 `docs/review/`：按 infra/01→13 顺序 43 个资源、40 张控制台截图、29 项只读校验
- **为什么改**：之后在 AWS 验证功能时可复用同一流程，方便 review
- **涉及文件/资源**：`~/.claude/skills/aws-deploy-evidence/**`、`docs/review/**`、`RUNBOOK.md`
- **结果**：29/29 PASS；修正过程中发现并修入 skill：Redshift IdC 连接页直链跳 dashboard（需从侧栏点入，侧栏需先展开 "Open navigation pane"）、校验命令变量需在 run.sh 内展开、Redshift 布尔值返回 't'；超高截图按页切片（Pillow）

## [2026-10-05] RUNBOOK / 邮件加入每一步的 AWS 控制台截图（含截图时完整 URL）
- **改了什么**：通过 agent-browser `--auto-connect` 连接用户已登录的 Chrome，只在新开的一个标签页中浏览只读控制台页面（完成后关闭），截取 19 张图到 `docs/img/console/`，`manifest.tsv` 记录每张图截图时的完整 URL 与时间；`docs/build_console_shots.py` 把截图插入 RUNBOOK 对应步骤（Step 1–4、6–12）并在邮件新增 Appendix A；PDF 重新生成（27 页）
- **为什么改**：便于读者对照控制台验证每一步配置
- **涉及文件/资源**：`docs/img/console/*.png`、`docs/img/console/manifest.tsv`、`docs/build_console_shots.py`、`RUNBOOK.md`、`docs/email-draft.html/.pdf`
- **结果**：每张图已目视检查；修正 3 处：IdC 设置需点 Authentication 页签（URL 不随页签变化）、Gateway 详情需从列表点入（直链会跳到首页）、IAM 角色内联策略需展开；未截取任何密钥页面

## [2026-10-05] 2LO / 3LO Web GUI（localhost:8081）
- **改了什么**：新增 `webchat/oauth_app.py` + `oauth_index.html`（调用独立 OAuth runtime）：2LO 面板（M2M token → Gateway → svc_reporting）、3LO 面板（同意登录 → AgentCore callback → CompleteResourceTokenAuth → Token Vault → userInfo，可选 force / prompt=login）；Cognito 客户端追加 8081 callback/logout；OAuth workload identity 追加 return URL `http://localhost:8081/3lo/callback`（保留 8765）
- **为什么改**：用户需要 2LO/3LO 的图形化测试界面
- **涉及文件/资源**：`webchat/oauth_app.py`、`webchat/oauth_index.html`、`infra/13-web-login-client.py`、`infra/12-deploy-oauth-runtime.sh`、workload identity `rsidc_oauth_agent-4lxrH9AmnT`
- **结果**：headless Chrome（zhang）验证：2LO 显示无用户的 token 与含 PII 的 5 行；3LO session binding OK、vault token 属于 zhang、identity guard 通过；8080 OBO GUI 不受影响

## [2026-10-05] 文档补充 IdC Trusted Token Issuer（"信任 Cognito 签发的 JWT"）
- **改了什么**：RUNBOOK 新增 Step 3a（TTI 配置表、两个引用它的 IdC 应用及 audience、IdC 交换时的 5 项校验、创建/验证命令及实际输出、设计注意点）；邮件新增 2.1 节（含控制台截图 `docs/img/idc-trusted-token-issuer.png`），原数据节改为 2.2；PDF 重新生成（11 页）
- **为什么改**：让读者理解 IdC 如何信任 Cognito JWT 并映射到 IdC 用户
- **涉及文件/资源**：`RUNBOOK.md`、`docs/email-draft.html/.pdf`、`docs/img/idc-trusted-token-issuer.png`、`tests/render_data_views.py`；TTI `tti-54429cde-c0b0-70e4-eeec-ba89c6508f18`（只读查询，未修改）
- **结果**：内容基于 describe-trusted-token-issuer / describe-redshift-idc-applications / get-application-grant 的实际输出；邮件 2.1 节目视检查通过

## [2026-10-05] 架构图加入 Web chat GUI（localhost:8080）
- **改了什么**：OBO 架构图新增 “Operator workstation” 分组（Web chat GUI + Operator tools），步骤改为 8 步（打开 GUI → Cognito managed login code+PKCE → Bearer JWT → IdC 交换 → LLM → NAT → Redshift → 运维路径）；同步更新 flow.html 的 OBO 动画、RUNBOOK 架构说明、邮件 Setup/Identity flow 并重新生成 PDF
- **为什么改**：用户以本地 GUI 作为 agent 的前端
- **涉及文件/资源**：`docs/architecture.svg/.tsx`、`docs/flow_template.html`、`docs/flow.html`、`RUNBOOK.md`、`docs/email-draft.html/.pdf`
- **结果**：架构图 headless Chrome 目视检查通过（无连线穿过图标/标题）；flow.html OBO 8 步无 JS 报错

## [2026-10-05] 本地 Web GUI（webchat）用于以终端用户身份测试 agent
- **改了什么**：`infra/13-web-login-client.py` 为现有 OBO Cognito 客户端开启 managed login（授权码 + PKCE，仅新增 OAuth 字段）；新增 `webchat/`（标准库 HTTP 服务，仅监听 127.0.0.1，token 只保存在服务端内存）：登录 → 聊天 / SQL → AgentCore Runtime（Bearer 用户 ID token）
- **为什么改**：用户需要 GUI 而非 CLI 来测试不同用户的数据访问
- **涉及文件/资源**：`webchat/app.py`、`webchat/index.html`、`webchat/README.md`、Cognito 客户端 kff7mg63m7d94n6f2euip41na（新增 callback http://localhost:8080/callback）
- **结果**：headless Chrome 端到端验证：wei 看到 5 行含 email；登出后 zhang 只看到 2 行 APAC 且 email 列被拒绝（42501）

## [2026-10-05] 邮件/RUNBOOK 加入 Redshift 数据与按用户可见性
- **改了什么**：新增 `tests/data_views.py`（以各 persona 身份经 OBO agent 执行同样的 SELECT *）与 `tests/render_data_views.py`（生成 `docs/data-views.md/.html`）；RUNBOOK Step 5 后与邮件 2.1 节插入 dev 库 3 张表全量数据 + 每个用户实际可见结果；新增发现：列级授权下 `SELECT *` 会静默去掉无权限列而不报错
- **为什么改**：便于向同事展示权限与数据访问效果
- **涉及文件/资源**：`tests/data_views.py`、`tests/render_data_views.py`、`tests/results-data-views.json`、`docs/data-views.*`、`RUNBOOK.md`、`docs/email-draft.*`
- **结果**：邮件 PDF 重新生成（9 页），2.1 节在 headless Chrome 中目视检查通过

## [2026-10-05] 动态流程图 docs/flow.html
- **改了什么**：基于两张架构图生成自包含的动画 HTML（OBO / 2LO / 3LO 三个标签），token 沿真实连线移动，LOGIN 标记登录点，徽章显示校验点（JWT 校验、IdC 交换、session binding、identity guard、Redshift 授权）
- **为什么改**：直观展示用户在哪里登录、JWT 及各类 token 如何流转
- **涉及文件/资源**：`docs/flow_template.html`、`docs/build_flow.py`、`docs/flow.html`
- **结果**：headless Chrome 中三个标签逐步播放，无 JS 报错；修复 caption 粗体换行问题

## [2026-10-04] 新增 2LO / 3LO 测试用例（不影响 OBO）
- **改了什么**：新建独立 runtime `rsidc_oauth_agent`；Cognito 同池新增 managed login v2 域名、resource server、2LO/3LO 客户端；AgentCore Identity 两个 CustomOauth2 credential provider；2LO 下游 = AgentCore Gateway(MCP, 仅允许 2LO client) → Lambda → Redshift 服务用户 svc_reporting；3LO 用 Token Vault + session binding（headless 浏览器自动完成同意）；agent 端身份校验 guard；第二张架构图；邮件新增第 5 节
- **为什么改**：对比 AgentCore Identity 的 2LO / 3LO 与 OBO 在同一 Redshift 数据上的访问控制差异
- **涉及文件/资源**：`infra/09-12`、`agent_oauth/`、`lambda/reporting/`、`tests/oauth_tests.py`、`docs/architecture-2lo-3lo.*`、`docs/email-draft.*`、`history/003-*`；Gateway `rsidc-2lo-gateway-mhss1cesvt`、runtime `rsidc_oauth_agent-*`、Lambda `rsidc-reporting`
- **结果**：2LO/3LO 18/18 断言通过 + 1 项观察（prompt=login 经 customParameters 后 token 未存入 vault）；发现 3LO 共享浏览器风险并以 agent 端 guard 修复；OBO 回归 16/16，OBO runtime 仍为 v3

## [2026-10-04] 邮件草稿：补充 AgentCore Identity 认证模式归类
- **改了什么**：阅读《AgentCore Identity Deep Dive》deck（SigV4/2LO/3LO/OBO），在邮件中新增 1.1 节与 TL;DR 条目：本测试验证的是 **OBO（token exchange）**，经 IdC 可信身份传播实现；并列出与 deck 中 OBO 流程的差异（交换由 agent 代码调用 CreateTokenWithIAM，而非 Credential Provider/Gateway TOKEN_EXCHANGE；下游 Redshift 只看到用户身份；为何不能直接转发 JWT）
- **为什么改**：同事需要按 AgentCore Identity 的标准模式理解测试结论
- **涉及文件/资源**：`docs/email-draft.html`、`docs/email-draft.pdf`
- **结果**：PDF 重新生成，Setup 节改为新页起始，避免标题孤行

## [2026-10-04] 架构图 + 邮件草稿 PDF
- **改了什么**：用 aws-architecture-diagram-svg skill 绘制测试架构图（用户→Cognito→AgentCore Runtime(VPC/NAT EIP)→IdC→Redshift、Bedrock、运维工作站）；生成给同事的邮件草稿 PDF（架构、配置、测试步骤、结果、发现、成本）
- **为什么改**：对外分享测试结论
- **涉及文件/资源**：`docs/architecture.svg`、`docs/architecture.tsx`、`docs/email-draft.html`、`docs/email-draft.pdf`
- **结果**：架构图在 headless Chrome 中目视检查通过（无连线穿过节点/分组标题，aspect 1.68）；PDF 共 4 页（A4）

## [2026-10-02] Cognito：所有 user pool 禁用自助注册
- **改了什么**：扫描全部区域 41 个 user pool，将仍允许自助注册的 6 个（us-east-1，均 0 用户）设为 AllowAdminCreateUserOnly=true
- **为什么改**：安全要求——仅管理员可创建用户
- **涉及文件/资源**：`infra/ops/cognito-disable-self-signup.py`；us-east-1_67YaKCmhR/8KbkOcNzT/JA2ECDabY/MAuafT7PT/UajACnw7W/hCgDYq4vq；`~/.claude/CLAUDE.md` 规则
- **结果**：每个 pool 前后 diff 仅此一项变化；dry-run 剩余 0；SignUp 调用返回 "SignUp is not permitted for this user pool"

## [2026-10-02] AgentCore Runtime × Redshift × IAM Identity Center access-control validation
- **改了什么**：新建 runtime VPC（NAT EIP 47.131.152.68）、Cognito user pool、IdC Trusted Token Issuer + Redshift IdC app（AWSIDC）、Redshift ra3.large（SG 仅允许工作站 2 个出口 IP + runtime EIP）、IdC 客户托管应用（token exchange）、AgentCore Runtime 数据 agent（VPC 模式、Cognito JWT 入站认证）；编写 16 项权限矩阵与负向/网络测试
- **为什么改**：验证 agent 访问 Redshift 时是否遵循 IdC 用户/组的访问控制，并限制网络来源
- **涉及文件/资源**：`infra/01-08,99`、`agent/`、`tests/`、`RUNBOOK.md`；Redshift `rsidc-cluster`（ap-east-1）、AgentCore `rsidc_data_agent-BoemCIApSW`（ap-southeast-1）、Cognito `ap-southeast-1_kSVpAo5yl`、IdC apps `apl-7158c218c69d902a` / `apl-7158676c1128adac`
- **结果**：矩阵 16/16 通过；无 token/伪造 token 401；JWT 重放被拒；SG 撤销后工作站超时；修复 2 个问题（history/001、002）。运行成本约 $0.72/小时，用完执行 `infra/99-teardown.sh`
