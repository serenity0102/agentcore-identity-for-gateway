"""Set AllowAdminCreateUserOnly=true on every Cognito user pool (all regions) that still allows self sign-up.
UpdateUserPool resets omitted settings to defaults, so the full current config is copied back and only
AdminCreateUserConfig.AllowAdminCreateUserOnly changes. Prints a before/after diff per pool. --dry-run to preview."""
import json, sys, boto3

DRY = "--dry-run" in sys.argv
s = boto3.Session()
regions = [r["RegionName"] for r in s.client("ec2", region_name="us-east-1").describe_regions()["Regions"]]
VOLATILE = {"LastModifiedDate", "EstimatedNumberOfUsers"}

def flat(d, p=""):
    out = {}
    for k, v in (d or {}).items():
        out.update(flat(v, f"{p}{k}.") if isinstance(v, dict) else {f"{p}{k}": v})
    return out

for region in regions:
    c = s.client("cognito-idp", region_name=region)
    try:
        pools = [p["Id"] for pg in c.get_paginator("list_user_pools").paginate(MaxResults=60) for p in pg["UserPools"]]
    except Exception:
        continue
    update_fields = c.meta.service_model.operation_model("UpdateUserPool").input_shape.members
    for pid in pools:
        before = c.describe_user_pool(UserPoolId=pid)["UserPool"]
        if before.get("AdminCreateUserConfig", {}).get("AllowAdminCreateUserOnly"):
            continue
        params = {k: v for k, v in before.items() if k in update_fields}
        params["UserPoolId"] = pid
        params["PoolName"] = before["Name"]
        params["UserPoolTags"] = before.get("UserPoolTags", {})
        acu = dict(before.get("AdminCreateUserConfig", {}))
        acu.pop("UnusedAccountValidityDays", None)  # deprecated; conflicts with PasswordPolicy.TemporaryPasswordValidityDays
        acu["AllowAdminCreateUserOnly"] = True
        params["AdminCreateUserConfig"] = acu
        print(f"== {region} {pid} ({before['Name']}) users={before.get('EstimatedNumberOfUsers')}")
        if DRY:
            continue
        try:
            c.update_user_pool(**params)
        except Exception as e:
            print(f"   FAILED: {type(e).__name__}: {e}")
            continue
        after = c.describe_user_pool(UserPoolId=pid)["UserPool"]
        b, a = flat(before), flat(after)
        diff = {k: (b.get(k), a.get(k)) for k in set(b) | set(a) if b.get(k) != a.get(k) and k.split(".")[0] not in VOLATILE}
        print("   changed:", json.dumps(diff, default=str))
