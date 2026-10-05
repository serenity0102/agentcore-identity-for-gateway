// 2LO / 3LO test case: separate AgentCore Runtime + AgentCore Identity credential providers / Token Vault + Gateway.
import { Diagram, Group, Node, Arrow, StepBadge, HStack, Move, Rect } from "../src/engine.tsx";
import { AmazonCognito, AmazonBedrockAgentCore, AWSLambda, AmazonRedshift } from "../src/icons/service.js";
import { Users } from "../src/icons/resource.js";

const steps = [
  "The user signs in to Amazon Cognito (ID token) and invokes the OAuth agent runtime. The inbound JWT authorizer validates it, and the runtime receives a workload access token bound to (agent, user).",
  "The agent calls AgentCore Identity GetResourceOauth2Token. 2LO (M2M): the credential provider runs a Cognito client_credentials grant, so the token represents the agent itself. 3LO (USER_FEDERATION): it returns a consent URL.",
  "3LO only: the user signs in at Cognito managed login. AgentCore Identity's callback exchanges the code, and the app completes session binding (CompleteResourceTokenAuth with the user's JWT). The token is stored in the Token Vault for (agent, user).",
  "3LO: the agent calls the user's API (Cognito userInfo) with the vault token, after checking that the token's email matches the caller.",
  "2LO: the agent calls the AgentCore Gateway (MCP). The Gateway's JWT authorizer allows only the 2LO client.",
  "The Gateway invokes the Lambda target with its IAM role.",
  "The Lambda queries Redshift as the shared service user svc_reporting (Data API). Every caller gets the same rows; IdC per-user grants and RLS do not apply.",
];

export default (
  <Diagram title="2LO / 3LO test case — AgentCore Identity credential providers, Token Vault and Gateway"
           layout="row" gap={48} align="center" steps={steps}>
    <Node id="users" icon={Users} label="End users" sub="wei / zhang / ds1 / temp users" />
    <Group kind="aws-cloud" id="cloud" label="AWS Cloud" layout="row" gap={48} align="center">
      <Group kind="region" id="sg" label="Region: ap-southeast-1 (Singapore)" layout="col" gap={48} align="start">
        <Move dx={232}><Node id="identity" icon={AmazonBedrockAgentCore} label="Amazon Bedrock AgentCore" sub="Identity · credential providers · Token Vault" /></Move>
        <HStack gap={56} align="center">
          <Group kind="vpc" id="vpc" label="VPC (10.50.0.0/16)">
            <Group kind="private-subnet" id="priv" label="Private Subnet">
              <Rect w={24} h={8} stroke="none" fill="none" />
              <Node id="agent" icon={AmazonBedrockAgentCore} label="Amazon Bedrock AgentCore" sub="Runtime · rsidc_oauth_agent" />
            </Group>
          </Group>
          <Node id="gw" icon={AmazonBedrockAgentCore} label="Amazon Bedrock AgentCore" sub="Gateway (MCP) · 2LO only" />
          <Node id="fn" icon={AWSLambda} label="AWS Lambda" sub="reporting tool" />
        </HStack>
        <Move dx={-16}><Node id="cognito" icon={AmazonCognito} label="Amazon Cognito" sub="user pool · managed login · 2LO/3LO clients" /></Move>
      </Group>
      <Group kind="region" id="hk" label="Region: ap-east-1 (Hong Kong)">
        <Node id="redshift" icon={AmazonRedshift} label="Amazon Redshift" sub="DB user svc_reporting" />
      </Group>
    </Group>

    <Arrow id="a1" from="users" to="agent" />
    <Arrow id="a3" from="users" to="cognito" fromSide="bottom" toSide="left" />
    <Arrow id="a2" from="agent" to="identity" fromSide="top" toSide="left" />
    <Arrow id="a5" from="agent" to="gw" />
    <Arrow id="a6" from="gw" to="fn" />
    <Arrow id="a7" from="fn" to="redshift" />

    <StepBadge n={1} on="a1" at="middle" />
    <StepBadge n={2} on="a2" at="end" dx={-48} />
    <StepBadge n={3} on="a3" at="middle" />
    <StepBadge n={4} near="cognito" dx={24} />
    <StepBadge n={5} on="a5" at="middle" />
    <StepBadge n={6} on="a6" at="middle" />
    <StepBadge n={7} on="a7" at="middle" />
  </Diagram>
);
