// AgentCore Runtime data agent → Redshift with IAM Identity Center trusted identity propagation.
// Source project: ~/projectlocal/agentcore-identity-for-gateway (RUNBOOK.md)
import { Diagram, Group, Node, Arrow, StepBadge, VStack, Move, Anchor, Rect } from "../src/engine.tsx";
import {
  AmazonCognito, AmazonBedrockAgentCore, AmazonBedrock, AWSIAMIdentityCenter, AmazonRedshift,
} from "../src/icons/service.js";
import { Users, Client, AmazonVPCNATGateway, GenericApplication } from "../src/icons/resource.js";

const steps = [
  "The user opens the local Web chat GUI at http://localhost:8080 (webchat/app.py, runs on the operator workstation, bound to 127.0.0.1) and clicks Sign in.",
  "Cognito managed login (authorization code + PKCE): the user signs in (users are admin-created; emails mirror IdC users). The GUI exchanges the code for the ID token (JWT) and keeps it server-side.",
  "The GUI invokes the AgentCore Runtime with the JWT as a bearer token. AgentCore Identity's JWT authorizer validates it (401 if missing or forged) and forwards the Authorization header to the agent.",
  "The agent exchanges the JWT once via sso-oauth:CreateTokenWithIAM on the customer-managed IdC app (Trusted Token Issuer: Cognito email → IdC user). Only the runtime role is allowed; admins are explicitly denied.",
  "The agent's LLM (Claude via Amazon Bedrock) plans the SQL and calls the run_sql tool.",
  "The runtime egresses from private subnets through the NAT gateway's fixed EIP 47.131.152.68.",
  "Redshift accepts 5439 only from the runtime EIP and the operator IPs (security group). The session runs as AWSIDC:<user>, so group-role GRANTs, column grants and RLS apply.",
  "Operator tools on the same workstation (tests, admin seeding via the Data API with a Secrets Manager secret) are the only other allowlisted source.",
];

export default (
  <Diagram title="AgentCore Runtime × Amazon Redshift × IAM Identity Center — identity-propagation test"
           layout="row" gap={48} align="center" steps={steps}>
    <VStack gap={88} align="center">
      <Node id="users" icon={Users} label="End users (browser)" sub="wei / zhang / chen / ds1" />
      <Group kind="generic" id="ws" label="Operator workstation (localhost)" layout="col" gap={88} align="center">
        <Node id="gui" icon={GenericApplication} label="Web chat GUI" sub="http://localhost:8080 · webchat/app.py" />
        <Node id="ops" icon={Client} label="Operator tools" sub="egress 15.248.4.71 / 15.248.5.7" />
      </Group>
    </VStack>

    <Group kind="aws-cloud" id="cloud" label="AWS Cloud (account 383386985941)" layout="row" gap={56} align="start">
      <Group kind="region" id="sg" label="Region: ap-southeast-1 (Singapore)" layout="col" gap={48} align="center">
        <Move dx={112}>
          <Node id="cognito" icon={AmazonCognito} label="Amazon Cognito" sub="user pool (admin-only)" />
        </Move>
        <Group kind="vpc" id="rt-vpc" label="VPC (10.50.0.0/16)" layout="row" gap={40} align="center">
          <Group kind="private-subnet" id="rt-priv" label="Private Subnet">
            <Rect w={24} h={8} stroke="none" fill="none" />
            <Node id="agent" icon={AmazonBedrockAgentCore} label="Amazon Bedrock AgentCore"
                  sub="Runtime (VPC) · data agent" />
          </Group>
          <Group kind="public-subnet" id="rt-pub" label="Public Subnet">
            <Node id="nat" icon={AmazonVPCNATGateway} label="NAT Gateway" sub="EIP 47.131.152.68" />
          </Group>
        </Group>
        <Move dx={-96}>
          <Node id="bedrock" icon={AmazonBedrock} label="Amazon Bedrock" sub="Claude Sonnet 5.5" />
        </Move>
      </Group>

      <Group kind="region" id="hk" label="Region: ap-east-1 (Hong Kong)" layout="col" gap={48} align="center">
        <Node id="idc" icon={AWSIAMIdentityCenter} label="AWS IAM Identity Center"
              sub="TTI · agent app · Redshift app" />
        <Group kind="vpc" id="hk-vpc" label="VPC (default)">
          <Group kind="public-subnet" id="hk-pub" label="Public Subnet (SG 5439 allowlist)">
            <Node id="redshift" icon={AmazonRedshift} label="Amazon Redshift"
                  sub="ra3.large · namespace AWSIDC" />
          </Group>
        </Group>
      </Group>
    </Group>

    <Arrow id="a0" from="users" to="gui" fromSide="bottom" toSide="top" />
    <Arrow id="a1" from="gui" to="cognito" riser={0.06} />
    <Arrow id="a2" from="gui" to="agent" />
    <Anchor id="wp-idc" x={552} y={208} />
    <Arrow id="a3" from="agent" to="wp-idc" fromSide="top" head="none" />
    <Arrow id="a3b" from="wp-idc" to="idc" toSide="bottom" />
    <Arrow id="a4" from="agent" to="bedrock" fromSide="bottom" toSide="top" />
    <Arrow id="a5" from="agent" to="nat" />
    <Arrow id="a6" from="nat" to="redshift" />
    <Anchor id="wp-ops" x={152} y={648} />
    <Arrow id="a7" from="ops" to="wp-ops" fromSide="bottom" head="none" />
    <Arrow id="a7b" from="wp-ops" to="redshift" toSide="bottom" />

    <StepBadge n={1} on="a0" at="middle" side="right" />
    <StepBadge n={2} on="a1" at="end" dx={-48} />
    <StepBadge n={3} on="a2" at="end" side="top" dx={-56} />
    <StepBadge n={4} on="a3b" at="middle" />
    <StepBadge n={5} on="a4" at="end" side="right" dx={16} />
    <StepBadge n={6} on="a5" at="middle" />
    <StepBadge n={7} on="a6" at="middle" side="bottom" dx={-40} />
    <StepBadge n={8} on="a7b" at="start" />
  </Diagram>
);
