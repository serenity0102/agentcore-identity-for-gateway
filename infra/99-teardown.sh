#!/usr/bin/env bash
# Deletes EVERYTHING created by steps 01-12 (reverse order). Irreversible: Redshift is deleted without a final snapshot.
# Does NOT touch the pre-existing IAM Identity Center instance, its users or groups.
set -uo pipefail; source "$(dirname "$0")/00-config.sh"
read -r -p "Type 'delete ${PROJECT}' to destroy all ${PROJECT} resources: " c; [ "$c" = "delete ${PROJECT}" ] || exit 1
x() { echo "+ $*"; "$@" >/dev/null || echo "  (skipped/failed)"; }
# 2LO/3LO test case: OAuth runtime, Gateway, Lambda, credential providers, roles
x aws bedrock-agentcore-control delete-agent-runtime --region $RT_REGION --agent-runtime-id $OAUTH_RT_ID
for t in $(aws bedrock-agentcore-control list-gateway-targets --region $RT_REGION --gateway-identifier $GW_ID --query 'items[].targetId' --output text 2>/dev/null); do
  x aws bedrock-agentcore-control delete-gateway-target --region $RT_REGION --gateway-identifier $GW_ID --target-id $t; done
sleep 10; x aws bedrock-agentcore-control delete-gateway --region $RT_REGION --gateway-identifier $GW_ID
x aws lambda delete-function --region $RT_REGION --function-name ${PROJECT}-reporting
for n in rsidc-2lo-cognito rsidc-3lo-cognito; do x aws bedrock-agentcore-control delete-oauth2-credential-provider --region $RT_REGION --name $n; done
x aws iam delete-role-policy --role-name ${PROJECT}-oauth-runtime-role --policy-name oauth-runtime; x aws iam delete-role --role-name ${PROJECT}-oauth-runtime-role
x aws iam delete-role-policy --role-name ${PROJECT}-reporting-lambda-role --policy-name reporting; x aws iam delete-role --role-name ${PROJECT}-reporting-lambda-role
x aws iam delete-role-policy --role-name ${PROJECT}-gateway-role --policy-name invoke-reporting; x aws iam delete-role --role-name ${PROJECT}-gateway-role
x aws cognito-idp delete-user-pool-domain --region $RT_REGION --user-pool-id $COGNITO_POOL_ID --domain ${PROJECT}-${ACCOUNT_ID}
# AgentCore runtime + artifacts
x aws bedrock-agentcore-control delete-agent-runtime --region $RT_REGION --agent-runtime-id $RT_ID
x aws s3 rm s3://${PROJECT}-artifacts-${ACCOUNT_ID}-${RT_REGION} --recursive
x aws s3api delete-bucket --bucket ${PROJECT}-artifacts-${ACCOUNT_ID}-${RT_REGION} --region $RT_REGION
# IdC applications + TTI (instance itself untouched)
x aws sso-admin delete-application --region $IDC_REGION --application-arn $AGENT_IDC_APP_ARN
x aws redshift delete-cluster --region $IDC_REGION --cluster-identifier $REDSHIFT_CLUSTER_ID --skip-final-cluster-snapshot
aws redshift wait cluster-deleted --region $IDC_REGION --cluster-identifier $REDSHIFT_CLUSTER_ID
x aws redshift delete-redshift-idc-application --region $IDC_REGION --redshift-idc-application-arn $REDSHIFT_IDC_APP_ARN
x aws sso-admin delete-trusted-token-issuer --region $IDC_REGION --trusted-token-issuer-arn $TTI_ARN
x aws redshift delete-cluster-subnet-group --region $IDC_REGION --cluster-subnet-group-name ${PROJECT}-subnets
x aws ec2 delete-security-group --region $IDC_REGION --group-id $RS_SG_ID
# IAM
for p in agent-runtime idc-token-exchange; do x aws iam delete-role-policy --role-name ${PROJECT}-agent-runtime-role --policy-name $p; done
x aws iam delete-role --role-name ${PROJECT}-agent-runtime-role
x aws iam delete-role-policy --role-name ${PROJECT}-redshift-idc-role --policy-name redshift-idc
x aws iam delete-role --role-name ${PROJECT}-redshift-idc-role
# Cognito
x aws cognito-idp delete-user-pool --region $RT_REGION --user-pool-id $COGNITO_POOL_ID
# Runtime VPC (AgentCore ENIs can take a while to release after runtime deletion)
R=$RT_REGION
x aws ec2 delete-nat-gateway --region $R --nat-gateway-id $RT_NAT_ID
aws ec2 wait nat-gateway-deleted --region $R --nat-gateway-ids $RT_NAT_ID
x aws ec2 release-address --region $R --allocation-id $RT_EIP_ALLOC
for i in $(seq 30); do n=$(aws ec2 describe-network-interfaces --region $R --filters Name=group-id,Values=$RT_SG_ID --query 'length(NetworkInterfaces)' --output text); [ "$n" = 0 ] && break; echo "  waiting for $n runtime ENIs to release..."; sleep 30; done
x aws ec2 delete-security-group --region $R --group-id $RT_SG_ID
for s in $RT_PUB_SUBNET $RT_PRIV_SUBNET_1 $RT_PRIV_SUBNET_2; do x aws ec2 delete-subnet --region $R --subnet-id $s; done
for t in $RT_PUB_RTB $RT_PRIV_RTB; do x aws ec2 delete-route-table --region $R --route-table-id $t; done
x aws ec2 detach-internet-gateway --region $R --internet-gateway-id $RT_IGW_ID --vpc-id $RT_VPC_ID
x aws ec2 delete-internet-gateway --region $R --internet-gateway-id $RT_IGW_ID
x aws ec2 delete-vpc --region $R --vpc-id $RT_VPC_ID
echo "Done. Remove infra/state.env and tests/.users.env if you will not redeploy."
