#!/usr/bin/env bash
# Deploy the two web GUIs (webchat/app.py = OBO, webchat/oauth_app.py = 2LO/3LO) as Lambda Function URLs (HTTPS, no ALB/EC2).
# Access control: the adapter only serves requests whose AWS-observed source IP is in WEB_ALLOWED_IPS (default: MY_IPS).
# Also registers the new URLs as Cognito callbacks (step 13) and as a 3LO return URL on the OAuth workload identity.
set -euo pipefail; source "$(dirname "$0")/00-config.sh"; R=$RT_REGION; ROOT="$(cd "$(dirname "$0")/.." && pwd)"
ROLE=${PROJECT}-webchat-role; # Function URLs are dual-stack, so browsers often arrive over IPv6: allow the IPv4s (/32) plus the current IPv6 /64.
V6=$(curl -s -6 --max-time 5 https://api64.ipify.org || true); V6=${V6:+$(python3 -c "import ipaddress,sys;print(ipaddress.ip_network(sys.argv[1]+'/64',strict=False))" $V6)}
IPS=${WEB_ALLOWED_IPS:-"$(for i in $MY_IPS; do echo -n "$i/32 "; done)$V6"}; echo "allowlisted IPs: $IPS"
aws iam get-role --role-name $ROLE >/dev/null 2>&1 || { aws iam create-role --role-name $ROLE --tags Key=Project,Value=$PROJECT --assume-role-policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Allow","Principal":{"Service":"lambda.amazonaws.com"},"Action":"sts:AssumeRole"}]}' >/dev/null; sleep 10; }
sed -e "s/__REGION__/$R/g" -e "s/__ACCOUNT__/$ACCOUNT_ID/g" -e "s/__WI__/$OAUTH_WI_NAME/g" "$ROOT/infra/policies/webchat-permissions.json" > /tmp/$ROLE.json
aws iam put-role-policy --role-name $ROLE --policy-name webchat --policy-document file:///tmp/$ROLE.json

B="$ROOT/build-webchat"; rm -rf "$B"; mkdir -p "$B/pkg/webchat" "$B/pkg/tests"
uv pip install -q --python-platform aarch64-manylinux2014 --python-version 3.12 --only-binary=:all: --target "$B/pkg" requests boto3
cp "$ROOT"/webchat/{app.py,oauth_app.py,lambda_adapter.py,index.html,oauth_index.html} "$B/pkg/webchat/"; cp "$ROOT/tests/invoke.py" "$B/pkg/tests/"
(cd "$B/pkg" && zip -qr "$B/webchat.zip" .)

deploy() {  # $1 = function suffix, $2 = WEBCHAT_APP module; prints the Function URL
  local FN=${PROJECT}-webchat-$1
  if aws lambda get-function --region $R --function-name $FN >/dev/null 2>&1; then
    aws lambda update-function-code --region $R --function-name $FN --zip-file fileb://$B/webchat.zip >/dev/null
  else
    aws lambda create-function --region $R --function-name $FN --runtime python3.12 --architectures arm64 --timeout 180 --memory-size 256 \
      --role arn:aws:iam::${ACCOUNT_ID}:role/$ROLE --handler webchat/lambda_adapter.handler --zip-file fileb://$B/webchat.zip \
      --tags Project=$PROJECT >/dev/null
    aws lambda wait function-active-v2 --region $R --function-name $FN
    aws lambda put-function-concurrency --region $R --function-name $FN --reserved-concurrent-executions 1 >/dev/null  # in-memory sessions
    aws lambda create-function-url-config --region $R --function-name $FN --auth-type NONE >/dev/null
    aws lambda add-permission --region $R --function-name $FN --statement-id url --action lambda:InvokeFunctionUrl --principal '*' --function-url-auth-type NONE >/dev/null
    aws lambda add-permission --region $R --function-name $FN --statement-id url-invoke --action lambda:InvokeFunction --principal '*' --invoked-via-function-url >/dev/null
  fi
  aws lambda wait function-updated-v2 --region $R --function-name $FN
  aws lambda get-function-url-config --region $R --function-name $FN --query FunctionUrl --output text | sed 's:/$::'
}
OBO_URL=$(deploy obo app); OAUTH_URL=$(deploy oauth oauth_app); save WEB_OBO_URL $OBO_URL; save WEB_OAUTH_URL $OAUTH_URL
COMMON="COGNITO_DOMAIN=$COGNITO_DOMAIN,COGNITO_CLIENT_ID=$COGNITO_CLIENT_ID,RT_REGION=$R,ALLOWED_IPS=${IPS}"
aws lambda update-function-configuration --region $R --function-name ${PROJECT}-webchat-obo \
  --environment "Variables={$COMMON,WEBCHAT_APP=app,RT_ARN=$RT_ARN,WEB_BASE_URL=$OBO_URL}" >/dev/null
aws lambda update-function-configuration --region $R --function-name ${PROJECT}-webchat-oauth \
  --environment "Variables={$COMMON,WEBCHAT_APP=oauth_app,OAUTH_RT_ARN=$OAUTH_RT_ARN,WEB_BASE_URL=$OAUTH_URL,OBO_WEB_URL=$OBO_URL}" >/dev/null
rm -rf "$B"

WEBCHAT_URLS="$OBO_URL $OAUTH_URL" "$ROOT/agent/.venv/bin/python" "$ROOT/infra/13-web-login-client.py"   # Cognito callback + logout URLs
CUR=$(aws bedrock-agentcore-control get-workload-identity --region $R --name $OAUTH_WI_NAME --query 'allowedResourceOauth2ReturnUrls' --output text)
aws bedrock-agentcore-control update-workload-identity --region $R --name $OAUTH_WI_NAME \
  --allowed-resource-oauth2-return-urls $(echo $CUR $OAUTH_URL/3lo/callback | tr ' ' '\n' | sort -u) >/dev/null
aws bedrock-agentcore-control get-workload-identity --region $R --name $OAUTH_WI_NAME --query allowedResourceOauth2ReturnUrls
echo "OBO GUI:     $OBO_URL"; echo "2LO/3LO GUI: $OAUTH_URL"
