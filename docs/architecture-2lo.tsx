// 2LO test case: the agent authenticates as ITSELF (client credentials) -> AgentCore Gateway -> Lambda -> Redshift service user.
import { Diagram, Group, Node, Arrow, StepBadge, HStack, Move, Rect, Raw, Anchor } from "../src/engine.tsx";
import { AmazonCognito, AmazonBedrockAgentCore, AWSLambda, AmazonRedshift } from "../src/icons/service.js";
import { Users } from "../src/icons/resource.js";
import { codePanel, panelHeight, authTable, authTableHeight, type CodeBlock, type AuthRow } from "./_codepanel.ts";

const steps = [
  "The user signs in to Amazon Cognito (managed login) and gets an ID token (JWT). This is the ONLY user login in 2LO.",
  "Runtime INBOUND auth: the user invokes the runtime with the Cognito ID token; the runtime JWT authorizer validates it against the Cognito pool (audience = OBO client) and hands the agent a workload access token (WAT).",
  "The agent asks AgentCore Identity for its OWN token: GetResourceOauth2Token(provider rsidc-2lo-cognito, oauth2Flow=M2M, scope rsidc-reports/read).",
  "Runtime OUTBOUND auth, brokered by AgentCore Identity: it runs client_credentials at the Cognito token endpoint with the 2LO client ID + secret (managed secret). Cognito issues the M2M token; its sub is the client, no user in it.",
  "Gateway INBOUND auth: the agent calls the Gateway with the M2M token. The Gateway's own JWT authorizer validates it against the SAME Cognito pool (JWKS) and allows only the 2LO client (user JWT 403, no token 401). AgentCore Identity is not involved here.",
  "Gateway OUTBOUND auth: the Gateway invokes the Lambda target with its IAM role (GATEWAY_IAM_ROLE).",
  "The Lambda queries Redshift through the Data API as the shared DB user svc_reporting. Every caller gets the same 5 rows including PII: IdC per-user grants and RLS do not apply.",
];

const CODE: CodeBlock[] = [
  { step: "3", title: "Agent: get its OWN token, M2M (agent_oauth/main.py)", lines: [
    "wat = BedrockAgentCoreContext.get_workload_access_token()   # delivered by the runtime",
    "tok = boto3.client(\"bedrock-agentcore\").get_resource_oauth2_token(",
    "    workloadIdentityToken=wat,",
    "    resourceCredentialProviderName=\"rsidc-2lo-cognito\",",
    "    scopes=[\"rsidc-reports/read\"], oauth2Flow=\"M2M\")[\"accessToken\"]" ] },
  { step: "4", title: "AgentCore Identity -> Cognito token endpoint (done for the agent)", lines: [
    "POST https://rsidc-383386985941.auth.ap-southeast-1.amazoncognito.com/oauth2/token",
    "  grant_type=client_credentials  scope=rsidc-reports/read",
    "  client_id=3lsr6jpphlql4hb8n1ge6a8sjp  client_secret=<managed secret>",
    "# -> access token: sub=client_id=3lsr6jpp..., scope=rsidc-reports/read, no username" ] },
  { step: "5", title: "Agent: call the Gateway tool with the M2M token", lines: [
    "POST https://rsidc-2lo-gateway-mhss1cesvt.gateway.bedrock-agentcore",
    "     .ap-southeast-1.amazonaws.com/mcp       Authorization: Bearer <m2m token>",
    "{\"jsonrpc\": \"2.0\", \"method\": \"tools/call\",",
    " \"params\": {\"name\": \"reporting___get_sales_report\", \"arguments\": {}}}",
    "# Gateway inbound: JWT authorizer, Cognito pool, allowedClients=[3lsr6jpp...]" ] },
  { step: "7", title: "Lambda: query Redshift as the service user (lambda/reporting)", lines: [
    "boto3.client(\"redshift-data\").execute_statement(",
    "    ClusterIdentifier=\"rsidc-cluster\", Database=\"dev\",",
    "    DbUser=\"svc_reporting\",            # GetClusterCredentials on this user only",
    "    Sql=\"SELECT TRIM(current_user), order_id, region, customer_email, ...\")",
    "# same result for wei / zhang / ds1" ] },
];
const AUTH: AuthRow[] = [
  { comp: "AgentCore Runtime", inbound: "Cognito JWT: user ID token (discovery = Cognito pool, aud = OBO client)", outbound: "AgentCore Identity → M2M token (client_credentials)" },
  { comp: "AgentCore Identity", inbound: "runtime's workload access token (WAT) + IAM role", outbound: "Cognito token endpoint with 2LO client ID + secret" },
  { comp: "AgentCore Gateway", inbound: "Cognito JWT: M2M token (same pool, JWKS), allowedClients = 2LO client", outbound: "Gateway IAM role → lambda:InvokeFunction" },
  { comp: "Lambda → Redshift", inbound: "invoked by the Gateway IAM role (identity policy)", outbound: "Data API + GetClusterCredentials as svc_reporting" },
];
const AUTH_H = authTableHeight(AUTH);
const PANEL_W = 1224, PANEL_H = panelHeight(CODE, 2, true);
const AUTH_Y = Number(process.env.AUTH_Y ?? 552);
const PANEL_X = Number(process.env.PANEL_X ?? 0), PANEL_Y = Number(process.env.PANEL_Y ?? 768);
const AX = Number(process.env.AX ?? 56), AY = Number(process.env.AY ?? 520), BX = Number(process.env.BX ?? 840);

export default (
  <Diagram title="2LO test case: the agent authenticates as itself (client credentials) → AgentCore Gateway → service account"
           layout="col" gap={64} align="start" steps={steps}>
   <HStack gap={48} align="center">
    <Node id="users" icon={Users} label="End users" sub="wei / zhang / ds1" />
    <Group kind="aws-cloud" id="cloud" label="AWS Cloud" layout="row" gap={48} align="start">
      <Group kind="region" id="sg" label="Region: ap-southeast-1 (Singapore)" layout="col" gap={56} align="start">
        <HStack gap={56} align="center">
          <Group kind="vpc" id="vpc" label="VPC (10.50.0.0/16)">
            <Group kind="private-subnet" id="priv" label="Private Subnet">
              <Rect w={24} h={8} stroke="none" fill="none" />
              <Node id="agent" icon={AmazonBedrockAgentCore} label="Amazon Bedrock AgentCore" sub="Runtime · rsidc_oauth_agent" />
            </Group>
          </Group>
          <Node id="gw" icon={AmazonBedrockAgentCore} label="Amazon Bedrock AgentCore" sub="Gateway (MCP) · inbound: 2LO client only" />
          <Node id="fn" icon={AWSLambda} label="AWS Lambda" sub="reporting tool" />
        </HStack>
        <HStack gap={120} align="center">
          <Move dx={24}><Node id="identity" icon={AmazonBedrockAgentCore} label="Amazon Bedrock AgentCore" sub="Identity · outbound broker · rsidc-2lo-cognito" /></Move>
          <Node id="cognito" icon={AmazonCognito} label="Amazon Cognito" sub="IdP · issues user JWT + M2M token" />
        </HStack>
      </Group>
      <Group kind="region" id="hk" label="Region: ap-east-1 (Hong Kong)">
        <Node id="redshift" icon={AmazonRedshift} label="Amazon Redshift" sub="DB user svc_reporting" />
      </Group>
    </Group>
   </HStack>
    <Group kind="borderless" id="authbox"><Rect w={PANEL_W} h={AUTH_H} stroke="none" fill="none" /></Group>
    <Group kind="borderless" id="codebox"><Rect w={PANEL_W} h={PANEL_H} stroke="none" fill="none" /></Group>
    <Raw>{authTable(PANEL_X, AUTH_Y, PANEL_W, "Auth boundaries: 2LO", AUTH)}</Raw>
    <Raw>{codePanel(PANEL_X, PANEL_Y, PANEL_W, "Key token code: 2LO (numbers = steps)", CODE, 2, true)}</Raw>

    <Anchor id="wp-login" x={AX} y={AY} />
    <Arrow id="a1" from="users" to="wp-login" fromSide="bottom" head="none" />
    <Anchor id="wp-login2" x={BX} y={AY} />
    <Arrow id="a1b" from="wp-login" to="wp-login2" head="none" />
    <Arrow id="a1c" from="wp-login2" to="cognito" toSide="right" />
    <Arrow id="a2" from="users" to="agent" />
    <Arrow id="a3" from="agent" to="identity" fromSide="bottom" toSide="top" />
    <Arrow id="a4" from="identity" to="cognito">client_credentials</Arrow>
    <Arrow id="a5" from="agent" to="gw" />
    <Arrow id="a6" from="gw" to="fn" />
    <Arrow id="a7" from="fn" to="redshift" />
    <Arrow id="ajwks" from="gw" to="cognito" dashed>inbound JWT check (JWKS)</Arrow>

    <StepBadge n={1} on="a1" at="middle" side="right" />
    <StepBadge n={2} on="a2" at="middle" />
    <StepBadge n={3} on="a3" at="middle" side="right" />
    <StepBadge n={4} on="a4" at="middle" side="bottom" />
    <StepBadge n={5} on="a5" at="end" dx={-32} />
    <StepBadge n={6} on="a6" at="middle" />
    <StepBadge n={7} on="a7" at="middle" />
  </Diagram>
);
