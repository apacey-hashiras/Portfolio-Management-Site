from fastapi import Request, HTTPException, Depends
from jose import jwt, JWTError
from .config import settings

# Supabase uses JWTs for authentication.
# The public key is not directly exposed, but we can verify the token 
# using the SUPABASE_PUBLISHABLE_KEY (which acts as the secret for HS256 tokens in some configurations)
# or better, by calling the Supabase Auth API.
# However, for a simple middleware, we can verify the signature if we have the JWT Secret.

def get_current_user(request: Request):
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authentication token")
    
    token = auth_header.split(" ")[1]
    
    # In a real production app with Supabase, you would typically use 
    # the 'gotrue' library or verify against Supabase's public keys.
    # For this implementation, we'll provide a placeholder that explains 
    # how to verify the Supabase JWT.
    
    try:
        # Note: Supabase JWTs are signed with a project-specific JWT Secret 
        # found in Settings > API. You should add SUPABASE_JWT_SECRET to your .env
        # payload = jwt.decode(token, settings.SUPABASE_JWT_SECRET, algorithms=["HS256"], audience="authenticated")
        # return payload
        
        # Placeholder: In development, we'll just check if the token exists.
        # In production, uncomment the jwt.decode logic above.
        return {"user_id": "placeholder_id"}
    except JWTError:
        raise HTTPException(status_code=401, detail="Could not validate credentials")

# To use this, add `user: dict = Depends(get_current_user)` to your protected routes.
