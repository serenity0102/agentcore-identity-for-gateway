"""Part 4 (customer version, tool RBAC for Amazon Quick): Cognito side.
  1. Cognito groups whose Description carries the group -> tool mapping (read by the Pre Token Gen trigger):
       mall-analyst -> all 4 tools (wei);  mall-viewer -> list + footfall only (ds1);  chen: no group
  2. App client rsidc-quick-mcp for Amazon Quick's MCP connector ("Custom user based OAuth"): confidential,
     authorization code, openid/email/profile, callbacks = Quick's /sn/oauthcallback per region (env QUICK_REDIRECTS adds more).
     ALLOW_ADMIN_USER_PASSWORD_AUTH (IAM-only) lets tests/mall_rbac_tests.py mint the same access token Quick gets.
     The client secret is written ONLY to tests/.quick-client.env (gitignored) and never printed.
Idempotent. Existing clients/pool settings are not modified."""
import os, subprocess, boto3

S = boto3.Session(profile_name="default"); R = os.environ["RT_REGION"]; POOL = os.environ["COGNITO_POOL_ID"]
idp = S.client("cognito-idp", region_name=R)
ROOT = os.path.join(os.path.dirname(__file__), "..")
GROUPS = {"mall-analyst": ("[rsidc-rbac] tools=Tools.Mall.List,Tools.Mall.Footfall,Tools.Mall.Hourly,Tools.Mall.Zone", ["wei"]),
          "mall-viewer": ("[rsidc-rbac] tools=Tools.Mall.List,Tools.Mall.Footfall", ["ds1"])}
QUICK_REGIONS = ["us-east-1", "us-west-2", "ap-southeast-2", "eu-west-1"]
CALLBACKS = [f"https://{r}.quicksight.aws.amazon.com/sn/oauthcallback" for r in QUICK_REGIONS] + os.environ.get("QUICK_REDIRECTS", "").split()


def save(k, v):
    subprocess.run(["bash", "-c", f'source "{ROOT}/infra/00-config.sh" >/dev/null; save {k} "{v}"'], check=True)


for name, (desc, members) in GROUPS.items():
    try:
        idp.create_group(UserPoolId=POOL, GroupName=name, Description=desc)
    except idp.exceptions.GroupExistsException:
        idp.update_group(UserPoolId=POOL, GroupName=name, Description=desc)
    for u in members:
        idp.admin_add_user_to_group(UserPoolId=POOL, Username=u, GroupName=name)
    got = idp.get_group(UserPoolId=POOL, GroupName=name)["Group"]["Description"]
    print(f"group {name:13} members={members} description={got!r}")

# Amazon Quick (MCP auth spec) sends RFC 8707 `resource=<gateway MCP URL>` on /authorize and /token. Cognito only honours a
# resource that is a REGISTERED resource server (URL identifier); otherwise /token fails with invalid_grant and Quick shows
# "No access token was found for an OAuth authorization code connection". See history/007.
GW_RES = os.environ["MALL_GW_URL"]
try:
    idp.describe_resource_server(UserPoolId=POOL, Identifier=GW_RES)
except idp.exceptions.ResourceNotFoundException:
    idp.create_resource_server(UserPoolId=POOL, Identifier=GW_RES, Name="rsidc-mall-gateway",
                               Scopes=[{"ScopeName": "invoke", "ScopeDescription": "Call the mall MCP tools"}])
    print("resource server created:", GW_RES)
SCOPES = ["openid", "email", "profile", f"{GW_RES}/invoke"]

cid = os.environ.get("QUICK_CLIENT_ID")
if not cid:
    c = idp.create_user_pool_client(
        UserPoolId=POOL, ClientName="rsidc-quick-mcp", GenerateSecret=True, AllowedOAuthFlows=["code"],
        AllowedOAuthScopes=SCOPES, AllowedOAuthFlowsUserPoolClient=True,
        SupportedIdentityProviders=["COGNITO"], CallbackURLs=CALLBACKS,
        ExplicitAuthFlows=["ALLOW_REFRESH_TOKEN_AUTH", "ALLOW_ADMIN_USER_PASSWORD_AUTH"],
        AccessTokenValidity=60, IdTokenValidity=60, RefreshTokenValidity=30,
        TokenValidityUnits={"AccessToken": "minutes", "IdToken": "minutes", "RefreshToken": "days"},
        PreventUserExistenceErrors="ENABLED", EnableTokenRevocation=True)["UserPoolClient"]
    cid = c["ClientId"]; save("QUICK_CLIENT_ID", cid)
else:
    c = idp.describe_user_pool_client(UserPoolId=POOL, ClientId=cid)["UserPoolClient"]
    missing = sorted(set(CALLBACKS) - set(c.get("CallbackURLs", []))) + sorted(set(SCOPES) - set(c.get("AllowedOAuthScopes", [])))
    if missing:  # UpdateUserPoolClient resets omitted fields: copy the full config back, then diff
        keep = ("ClientName", "RefreshTokenValidity", "AccessTokenValidity", "IdTokenValidity", "TokenValidityUnits",
                "ExplicitAuthFlows", "SupportedIdentityProviders", "CallbackURLs", "LogoutURLs", "AllowedOAuthFlows",
                "AllowedOAuthScopes", "AllowedOAuthFlowsUserPoolClient", "PreventUserExistenceErrors", "EnableTokenRevocation",
                "EnablePropagateAdditionalUserContextData", "AuthSessionValidity")
        upd = {k: c[k] for k in keep if k in c}; upd["CallbackURLs"] = sorted(set(c.get("CallbackURLs", [])) | set(CALLBACKS))
        upd["AllowedOAuthScopes"] = sorted(set(c.get("AllowedOAuthScopes", [])) | set(SCOPES))
        idp.update_user_pool_client(UserPoolId=POOL, ClientId=cid, **upd)
        a = idp.describe_user_pool_client(UserPoolId=POOL, ClientId=cid)["UserPoolClient"]
        print("client diff:", {k: (c.get(k), a.get(k)) for k in set(c) | set(a)
                               if k not in ("LastModifiedDate", "ClientSecret") and c.get(k) != a.get(k)})
        c = a
with open(os.path.join(ROOT, "tests/.quick-client.env"), "w") as f:  # gitignored; secret never printed
    f.write(f"QUICK_CLIENT_ID={cid}\nQUICK_CLIENT_SECRET={c['ClientSecret']}\n")
os.chmod(os.path.join(ROOT, "tests/.quick-client.env"), 0o600)
try:
    idp.describe_managed_login_branding_by_client(UserPoolId=POOL, ClientId=cid)
except idp.exceptions.ResourceNotFoundException:  # managed login v2 needs a branding per client
    idp.create_managed_login_branding(UserPoolId=POOL, ClientId=cid, UseCognitoProvidedValues=True)
c = idp.describe_user_pool_client(UserPoolId=POOL, ClientId=cid)["UserPoolClient"]
print(f"client rsidc-quick-mcp id={cid} flows={c['AllowedOAuthFlows']} scopes={c['AllowedOAuthScopes']} secret=<in tests/.quick-client.env>")
print("callbacks:", c["CallbackURLs"])
pool = idp.describe_user_pool(UserPoolId=POOL)["UserPool"]
print("AllowAdminCreateUserOnly:", pool["AdminCreateUserConfig"]["AllowAdminCreateUserOnly"])
