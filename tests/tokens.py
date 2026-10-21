"""Get Cognito tokens (ID / access) for a test persona (passwords in tests/.users.env, local only)."""
import os, boto3

def load_pw(user):
    for line in open(os.path.join(os.path.dirname(__file__), ".users.env")):
        k, _, v = line.strip().partition("=")
        if k == f"PW_{user}":
            return v
    raise KeyError(user)

def tokens(user):
    c = boto3.Session(profile_name="default").client("cognito-idp", region_name=os.environ["RT_REGION"])
    return c.initiate_auth(ClientId=os.environ["COGNITO_CLIENT_ID"], AuthFlow="USER_PASSWORD_AUTH",
                           AuthParameters={"USERNAME": user, "PASSWORD": load_pw(user)})["AuthenticationResult"]

def access_token(user):
    return tokens(user)["AccessToken"]

def id_token(user):
    c = boto3.Session(profile_name="default").client("cognito-idp", region_name=os.environ["RT_REGION"])
    r = c.initiate_auth(ClientId=os.environ["COGNITO_CLIENT_ID"], AuthFlow="USER_PASSWORD_AUTH",
                        AuthParameters={"USERNAME": user, "PASSWORD": load_pw(user)})
    return r["AuthenticationResult"]["IdToken"]
