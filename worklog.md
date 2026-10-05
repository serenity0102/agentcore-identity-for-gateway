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
