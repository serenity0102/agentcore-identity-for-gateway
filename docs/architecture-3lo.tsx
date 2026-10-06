// 3LO test case: the user consents once; AgentCore Identity keeps the USER's token in the Token Vault.
import { Diagram, Group, Node, Arrow, StepBadge, HStack, VStack, Move, Rect, Raw, Anchor } from "../src/engine.tsx";
import { AmazonCognito, AmazonBedrockAgentCore } from "../src/icons/service.js";
import { Users, GenericApplication } from "../src/icons/resource.js";
import { codePanel, panelHeight, authTable, authTableHeight, type CodeBlock, type AuthRow } from "./_codepanel.ts";

const steps = [
  "LOGIN 1/2 (app sign-in): the user opens the 2LO/3LO Web GUI (http://localhost:8081) and signs in at Cognito managed login; the GUI exchanges the code for an ID token (JWT) and keeps it server-side.",
  "Runtime INBOUND auth: the GUI invokes the runtime with the Cognito ID token; the runtime JWT authorizer validates it against the Cognito pool (audience = OBO client) and hands the agent a workload access token (WAT) bound to (agent, user).",
  "Runtime OUTBOUND auth, brokered by AgentCore Identity: GetResourceOauth2Token(provider rsidc-3lo-cognito, USER_FEDERATION). The Token Vault has nothing for (agent, user) yet, so it returns an authorization URL + sessionUri.",
  "LOGIN 2/2 (consent): the user opens the URL and signs in at Cognito managed login (PKCE + state added by AgentCore). Cognito redirects the code to the AgentCore Identity callback, which exchanges it with the 3LO client.",
  "Session binding: AgentCore redirects the browser to the app return URL (/3lo/callback?session_id=…). The GUI calls CompleteResourceTokenAuth(sessionUri, the user's JWT); only the user who started the flow can complete it. The token is stored in the Token Vault for (agent, user).",
  "Next call (any runtime session): GetResourceOauth2Token returns the user's own access token from the vault; no consent needed. The agent's identity guard checks the token's email equals the caller's.",
  "The agent calls the user's API (Cognito userInfo) with the user's token; Cognito itself validates that token (no Gateway in 3LO) and returns that user's own profile.",
];

const CODE: CodeBlock[] = [
  { step: "3", title: "Agent: ask for the USER's token (agent_oauth/main.py)", lines: [
    "wat = BedrockAgentCoreContext.get_workload_access_token()   # (agent, user)",
    "r = boto3.client(\"bedrock-agentcore\").get_resource_oauth2_token(",
    "    workloadIdentityToken=wat, resourceCredentialProviderName=\"rsidc-3lo-cognito\",",
    "    scopes=[\"openid\", \"email\", \"profile\"], oauth2Flow=\"USER_FEDERATION\",",
    "    resourceOauth2ReturnUrl=\"http://localhost:8081/3lo/callback\")",
    "# vault empty -> r[\"authorizationUrl\"], r[\"sessionUri\"] (valid 10 min)" ] },
  { step: "4", title: "Browser consent (LOGIN 2) and AgentCore callback", lines: [
    "GET <authorizationUrl>  -> Cognito managed login (code + PKCE + state)",
    "Cognito -> https://bedrock-agentcore.ap-southeast-1.amazonaws.com",
    "           /identities/oauth2/callback/9cb308bc-...   (3LO client callback)",
    "# AgentCore Identity exchanges the code with client 4mrecmrv4divtcngq62to3run1" ] },
  { step: "5", title: "App callback: session binding (webchat/oauth_app.py)", lines: [
    "# browser -> http://localhost:8081/3lo/callback?session_id=<sessionUri>",
    "boto3.client(\"bedrock-agentcore\").complete_resource_token_auth(",
    "    sessionUri=session_uri,",
    "    userIdentifier={\"userToken\": user_id_token})   # the signed-in app user",
    "# wrong user's JWT -> AccessDeniedException; OK -> Token Vault (agent, user)" ] },
  { step: "6", title: "Next call: user token from the vault + identity guard", lines: [
    "r = identity.get_resource_oauth2_token(..., sessionUri=session_uri)",
    "user_token = r[\"accessToken\"]           # wei's own token (no consent needed)",
    "if userinfo(user_token)[\"email\"] != caller_email:",
    "    return {\"status\": \"IDENTITY_MISMATCH\"}   # shared-browser guard" ] },
  { step: "7", title: "Agent: call the user's API with the user's token", lines: [
    "GET https://rsidc-383386985941.auth.ap-southeast-1.amazoncognito.com/oauth2/userInfo",
    "  Authorization: Bearer <user_token>",
    "# -> {\"username\": \"wei\", \"email\": \"wei@techfinance.example.com\", ...}" ] },
];
const AUTH: AuthRow[] = [
  { comp: "AgentCore Runtime", inbound: "Cognito JWT: user ID token (discovery = Cognito pool, aud = OBO client)", outbound: "AgentCore Identity → user token from Token Vault" },
  { comp: "AgentCore Identity", inbound: "runtime WAT (agent + user) + IAM role; app: CompleteResourceTokenAuth", outbound: "Cognito: authorization code exchange with 3LO client" },
  { comp: "Cognito userInfo (resource)", inbound: "user's access token, validated by Cognito itself", outbound: "-" },
  { comp: "Web GUI (8081)", inbound: "browser session cookie (ID token kept server-side)", outbound: "Bearer user JWT → runtime; CompleteResourceTokenAuth" },
];
const AUTH_H = authTableHeight(AUTH);
const PANEL_W = Number(process.env.PANEL_W ?? 1224), PANEL_H = panelHeight(CODE, 2, true);
const AUTH_Y = Number(process.env.AUTH_Y ?? 560);
const PANEL_X = Number(process.env.PANEL_X ?? 0), PANEL_Y = Number(process.env.PANEL_Y ?? 776);
const GX = Number(process.env.GX ?? 168), BY = Number(process.env.BY ?? 528), RX = Number(process.env.RX ?? 1136);

export default (
  <Diagram title="3LO test case: the user consents once; AgentCore Identity keeps the user's token in the Token Vault"
           layout="col" gap={64} align="start" steps={steps}>
   <HStack gap={48} align="center">
    <VStack gap={80} align="center">
      <Node id="users" icon={Users} label="End users (browser)" sub="wei / zhang / ds1" />
      <Group kind="generic" id="ws" label="Operator workstation (localhost)">
        <Node id="gui" icon={GenericApplication} label="2LO/3LO Web GUI" sub="http://localhost:8081 · webchat/oauth_app.py" />
      </Group>
    </VStack>
    <Group kind="aws-cloud" id="cloud" label="AWS Cloud">
      <Group kind="region" id="sg" label="Region: ap-southeast-1 (Singapore)" layout="col" gap={64} align="start">
        <HStack gap={160} align="start">
          <Move dx={48}><Node id="cognito" icon={AmazonCognito} label="Amazon Cognito" sub="IdP (LOGIN 1 + 2) · userInfo API" /></Move>
          <Node id="identity" icon={AmazonBedrockAgentCore} label="Amazon Bedrock AgentCore" sub="Identity · outbound broker · rsidc-3lo-cognito · Token Vault" />
        </HStack>
        <Group kind="vpc" id="vpc" label="VPC (10.50.0.0/16)">
          <Group kind="private-subnet" id="priv" label="Private Subnet">
            <Rect w={24} h={8} stroke="none" fill="none" />
            <Node id="agent" icon={AmazonBedrockAgentCore} label="Amazon Bedrock AgentCore" sub="Runtime · rsidc_oauth_agent" />
          </Group>
        </Group>
      </Group>
    </Group>
   </HStack>
    <Group kind="borderless" id="authbox"><Rect w={PANEL_W} h={AUTH_H} stroke="none" fill="none" /></Group>
    <Group kind="borderless" id="codebox"><Rect w={PANEL_W} h={PANEL_H} stroke="none" fill="none" /></Group>
    <Raw>{authTable(PANEL_X, AUTH_Y, PANEL_W, "Auth boundaries: 3LO", AUTH)}</Raw>
    <Raw>{codePanel(PANEL_X, PANEL_Y, PANEL_W, "Key token code: 3LO (numbers = steps)", CODE, 2, true)}</Raw>

    <Arrow id="aU" from="users" to="gui" fromSide="bottom" toSide="top">browser</Arrow>
    <Arrow id="aL" from="users" to="cognito" />
    <Arrow id="aI" from="gui" to="agent" />
    <Arrow id="aV" from="agent" to="identity" fromSide="right" toSide="bottom" />
    <Arrow id="aC" from="cognito" to="identity" />
    <Anchor id="wb1" x={GX} y={BY} />
    <Anchor id="wb2" x={RX} y={BY} />
    <Arrow id="aB1" from="gui" to="wb1" fromSide="bottom" head="none" />
    <Arrow id="aB2" from="wb1" to="wb2" head="none" />
    <Arrow id="aB3" from="wb2" to="identity" toSide="right" />
    <Arrow id="aUI" from="agent" to="cognito" fromSide="top" toSide="bottom" />

    <StepBadge n={1} on="aL" at="start" />
    <StepBadge n={2} on="aI" at="middle" />
    <StepBadge n={3} on="aV" at="start" dx={128} />
    <StepBadge n={4} on="aC" at="middle" />
    <StepBadge n={5} on="aB3" at="middle" side="left" />
    <StepBadge n={6} on="aV" at="start" dx={216} />
    <StepBadge n={7} on="aUI" at="middle" side="right" dy={-40} />
  </Diagram>
);
