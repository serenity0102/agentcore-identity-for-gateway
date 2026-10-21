# Shared configuration for all infra scripts. Source this file; do not execute.
export AWS_PROFILE=default
export PROJECT=rsidc
export IDC_REGION=ap-east-1          # IAM Identity Center + Redshift
export RT_REGION=ap-southeast-1      # AgentCore Runtime (nearest region with AgentCore)
export IDC_INSTANCE_ARN=arn:aws:sso:::instance/ssoins-715869a9a6444dc5
export IDENTITY_STORE_ID=d-c4670751e2
export ACCOUNT_ID=${ACCOUNT_ID:-$(aws sts get-caller-identity --query Account --output text)}   # looked up, not hardcoded
export REDSHIFT_CLUSTER_ID=${PROJECT}-cluster
export REDSHIFT_DB=dev
export REDSHIFT_NAMESPACE=AWSIDC     # IdC identities appear in Redshift as AWSIDC:<user> / AWSIDC:<group>
# Operator egress IPs (space-separated). Corp networks may NAT different ports via different IPs, so detect
# the IP actually used for TCP 5439 (portquiz) as well as HTTPS (checkip).
export MY_IPS=${MY_IPS:-"$( (curl -s --max-time 5 http://portquiz.net:5439 | grep -o 'Your IP: [0-9.]*' | cut -d' ' -f3; curl -s https://checkip.amazonaws.com) | sort -u | xargs)"}
STATE_FILE="$(dirname "${BASH_SOURCE[0]}")/state.env"
touch "$STATE_FILE"; source "$STATE_FILE"
save() { sed -i '' "/^export $1=/d" "$STATE_FILE"; echo "export $1=$2" >> "$STATE_FILE"; export "$1=$2"; }
