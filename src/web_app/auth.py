"""
Dependencies and middleware for JWT verification using Auth0.
"""
import os
import jwt
from fastapi import Request, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Dict, Any
from urllib.request import urlopen
import json

AUTH0_DOMAIN = os.getenv("AUTH0_DOMAIN", "")
AUTH0_AUDIENCE = os.getenv("AUTH0_AUDIENCE", "")
ALGORITHMS = ["RS256"]

security = HTTPBearer()

def get_rsa_key(token: str) -> Dict[str, Any]:
    """Fetch the JWKS from Auth0 to verify the token signature."""
    if not AUTH0_DOMAIN:
        raise HTTPException(status_code=500, detail="AUTH0_DOMAIN not configured backend")
        
    jwks_url = f"https://{AUTH0_DOMAIN}/.well-known/jwks.json"
    with urlopen(jwks_url) as response:
        jwks = json.loads(response.read().decode("utf-8"))
        
    try:
        unverified_header = jwt.get_unverified_header(token)
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token header")
        
    rsa_key = {}
    for key in jwks["keys"]:
        if key["kid"] == unverified_header["kid"]:
            rsa_key = {
                "kty": key["kty"],
                "kid": key["kid"],
                "use": key["use"],
                "n": key["n"],
                "e": key["e"]
            }
            break
            
    if not rsa_key:
        raise HTTPException(status_code=401, detail="Unable to find appropriate key")
        
    return rsa_key


def verify_token(credentials: HTTPAuthorizationCredentials = Security(security)) -> str:
    """
    Validates a JWT token using Auth0's public JWKS.
    Returns the Auth0 User ID (`sub` claim) if valid, otherwise raises a 401.
    """
    token = credentials.credentials
    rsa_key = get_rsa_key(token)
    
    try:
        payload = jwt.decode(
            token,
            key=jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(rsa_key)),
            algorithms=ALGORITHMS,
            audience=AUTH0_AUDIENCE,
            issuer=f"https://{AUTH0_DOMAIN}/"
        )
        # The 'sub' claim usually contains the user's permanent ID (e.g., 'google-oauth2|123456')
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Token missing subject claim")
            
        return user_id
        
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token is expired")
    except jwt.JWTClaimsError:
        raise HTTPException(status_code=401, detail="Invalid claims, check audience and issuer")
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"Unable to parse authentication token: {str(e)}")
