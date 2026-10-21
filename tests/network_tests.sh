#!/usr/bin/env bash
# Network + exchange-boundary checks. Run via: infra/run.sh tests/network_tests.sh
set -uo pipefail; D="$(cd "$(dirname "$0")" && pwd)"; PY="$D/../.venv/bin/python"
echo "### NET1 source IPs Redshift saw for IdC users (stl_connection_log)"
cat > /tmp/q.sql <<'SQL'
SELECT DISTINCT TRIM(remotehost) AS source_ip, TRIM(username) AS redshift_user FROM stl_connection_log WHERE username LIKE 'AWSIDC:%' AND event='authenticated' ORDER BY 1,2;
SQL
"$PY" - <<'PY'
import os, time, boto3
rs = boto3.Session(profile_name="default").client("redshift-data", region_name=os.environ["IDC_REGION"])
r = rs.execute_statement(ClusterIdentifier=os.environ["REDSHIFT_CLUSTER_ID"], Database="dev", SecretArn=os.environ["REDSHIFT_ADMIN_SECRET_ARN"], Sql=open("/tmp/q.sql").read())
while rs.describe_statement(Id=r["Id"])["Status"] not in ("FINISHED","FAILED"): time.sleep(0.5)
for row in rs.get_statement_result(Id=r["Id"])["Records"]: print(" ", row[0]["stringValue"], row[1]["stringValue"])
PY
echo; echo "### NET2 workstation TCP 5439 with SG rule present"; nc -vz -G 5 $REDSHIFT_HOST 5439 2>&1 | sed 's/^/  /'
echo "### NET3 revoke workstation rules -> expect timeout"
for ip in $MY_IPS; do aws ec2 revoke-security-group-ingress --region $IDC_REGION --group-id $RS_SG_ID --protocol tcp --port 5439 --cidr $ip/32 >/dev/null; done
sleep 5; nc -vz -G 5 $REDSHIFT_HOST 5439 2>&1 | sed 's/^/  /'
echo "### NET4 runtime still works while workstation is blocked (runtime egress = NAT EIP $RT_NAT_EIP)"
(cd "$D" && "$PY" -c "from invoke import invoke; from tokens import id_token; print(' ', invoke(id_token('chen'), {'sql':'SELECT current_user'}))")
echo "### NET5 restore workstation rules"
for ip in $MY_IPS; do aws ec2 authorize-security-group-ingress --region $IDC_REGION --group-id $RS_SG_ID --ip-permissions "[{\"IpProtocol\":\"tcp\",\"FromPort\":5439,\"ToPort\":5439,\"IpRanges\":[{\"CidrIp\":\"$ip/32\",\"Description\":\"operator workstation\"}]}]" >/dev/null; done
sleep 5; nc -vz -G 5 $REDSHIFT_HOST 5439 2>&1 | sed 's/^/  /'
aws ec2 describe-security-groups --region $IDC_REGION --group-ids $RS_SG_ID --query 'SecurityGroups[0].IpPermissions[0].IpRanges[].[CidrIp,Description]' --output text | sed 's/^/  /'
echo "### X1 admin IAM user (not in IdC app ActorPolicy) tries to exchange wei's JWT -> expect AccessDenied"
(cd "$D" && "$PY" - <<'PY'
import os, boto3
from tokens import id_token
try:
    boto3.Session(profile_name="default").client("sso-oidc", region_name=os.environ["IDC_REGION"]).create_token_with_iam(
        clientId=os.environ["AGENT_IDC_APP_ARN"], grantType="urn:ietf:params:oauth:grant-type:jwt-bearer", assertion=id_token("wei"))
    print("  UNEXPECTED: exchange succeeded")
except Exception as e: print(" ", type(e).__name__, str(e)[:200])
PY
)
