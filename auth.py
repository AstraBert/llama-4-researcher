from supabase import create_client
from hashlib import sha256

with open("/run/secrets/supabase_api_key") as f:
    supa_key = f.read()
f.close()
with open("/run/secrets/supabase_api_url") as g:
    supa_url = g.read()
g.close()

class Encrypter:
    def __init__(self):
        self.encrypter = sha256
    def encrypt(self, string: str) -> str:
        buffer = string.encode()
        enc = self.encrypter(buffer)
        return enc.hexdigest()
    
encryption = Encrypter()
supa_client = create_client(supabase_key=supa_key, supabase_url=supa_url)

def authenticate_user(username: str, password: str):
    response = supa_client.from_("users").select("*").eq("username", username).eq("password", encryption.encrypt(password)).execute()
    data = response.data
    if len(data) > 0:
        return True
    else:
        return False