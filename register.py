import gradio as gr
from pydantic import BaseModel, model_validator, validate_email, ValidationError
from pydantic_core import PydanticCustomError
from typing_extensions import Self
from supabase import create_client
from hashlib import sha256
import secrets

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

def contains_special_characters(password: str):
    special_chars = ["!", "?", "_", "$", "£", "-"]
    for char in special_chars:
        if char in password:
            return True
    return False

def contains_numbers(password: str):
    numbers = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]
    for char in numbers:
        if char in password:
            return True
    return False

def contains_capital_letters(password: str):
    if password.lower() == password:
        return False
    return True

class PasswordChange(BaseModel):
    old_password: str
    new_password: str
    @model_validator(mode="after")
    def validate_password(self) -> Self:
        if self.new_password == self.old_password:
            raise ValueError("The new password cannot be the same as the old password!")
        elif len(self.new_password) < 6:
            raise ValueError("The password should be 6 characters or more")
        elif not contains_special_characters(self.new_password):
            raise ValueError("The password should contain at least one special character among these: " + ", ".join(["!", "?", "_", "$", "£", "-"]))
        elif not contains_numbers(self.new_password):
            raise ValueError("The password should contain at least one number")
        elif not contains_capital_letters(self.new_password):
            raise ValueError("The password should contain at least one capital letter")
        else:
            return self

class Credentials(BaseModel):
    username: str
    email: str
    password: str
    confirm_password: str
    @model_validator(mode="after")
    def validate_credentials(self) -> Self:
        try:
            val, name = validate_email(self.email)
        except PydanticCustomError:
            raise ValueError("The provided email address is not valid")
        else:
            if self.password != self.confirm_password:
                raise ValueError("The provided passwords do not match")
            elif len(self.password) < 6:
                raise ValueError("The password should be 6 characters or more")
            elif not contains_special_characters(self.password):
                raise ValueError("The password should contain at least one special character among these: " + ", ".join(["!", "?", "_", "$", "£", "-"]))
            elif not contains_numbers(self.password):
                raise ValueError("The password should contain at least one number")
            elif not contains_capital_letters(self.password):
                raise ValueError("The password should contain at least one capital letter")
            else:
                if self.username != "":
                    return self
                else:
                    raise ValueError("The username must be a non-null string")

supa_client = create_client(supabase_key=supa_key, supabase_url=supa_url)

def register(us: str, em: str, psw: str, cpsw: str):
    try:
        credentials = Credentials(username=us, email=em, password=psw, confirm_password=cpsw)
    except ValidationError as e:
        raise gr.Error(message=e.errors(include_url=False, include_context=False)[0]['msg'], duration=15, title="Sign-Up Error")
    else:
        users = supa_client.table("users").select("*").eq("username", us).execute()
        emails = supa_client.table("users").select("*").eq("email", em).execute()
        if len(users.data) > 0:
            raise gr.Error(message="Sign-Up failed! The username already exists!", duration=15, title="Sign-Up Error")
        elif len(emails.data) > 0:
            raise gr.Error(message="Sign-Up failed! The e-mail address is already registered!", duration=15, title="Sign-Up Error")
        else:
            supa_client.table("users").insert({"username": credentials.username, "email": credentials.email, "password": encryption.encrypt(credentials.password)}).execute()
            gr.Info("Sign-Up was successful! You can now proceed to https://app.llamaresearcher.com", duration=15, title="Sign-Up Info")

def change_password(username: str, email: str, old_password: str, new_password: str):
    try:
        pswc = PasswordChange(old_password=old_password, new_password=new_password)
    except ValidationError as e:
        raise gr.Error(message=e.errors(include_url=False, include_context=False)[0]['msg'], duration=15, title="Password Change Error")
    else:
        user = supa_client.table("users").select("*").eq("username", username).eq("email", email).eq("password", encryption.encrypt(old_password)).execute()
        if len(user.data) == 0:
            raise gr.Error(message=f"There is no user with username {username} and e-mail {email} that matches with the old password you provided.", duration=15, title="Password Change Error")
        else:
            supa_client.table("users").update({"password": encryption.encrypt(pswc.new_password)}).eq("username", username).eq("email", email).execute()
            gr.Info("Password change was successful! You can now proceed to https://app.llamaresearcher.com", duration=15, title="Password Change Info")

def recover_password(username: str, email: str):
    user = supa_client.table("users").select("*").eq("username", username).eq("email", email).execute()
    if len(user.data) == 0:
        raise gr.Error(message=f"There is no user with username {username} and e-mail {email}.", duration=15, title="Password Recovery Error")
    else:
        new_password = secrets.token_urlsafe(32)
        supa_client.table("users").update({"password": encryption.encrypt(new_password)}).eq("username", username).eq("email", email).execute()
        gr.Info("Password recovery was successful! Please, change the password before you log in again", duration=15, title="Password Change Info")
        return new_password
        
reg = gr.Interface(fn=register, inputs=[gr.Textbox(label="Username"), gr.Textbox(label="Email Address", type="text"), gr.Textbox(label="Password", type="password"), gr.Textbox(label="Confirm Password", type="password")], outputs=None)
chan = gr.Interface(fn=change_password, inputs=[gr.Textbox(label="Username"), gr.Textbox(label="Email Address", type="text"), gr.Textbox(label="Old Password", type="password"), gr.Textbox(label="New Password", type="password")], outputs=None)
rec = gr.Interface(fn=recover_password, inputs=[gr.Textbox(label="Username"), gr.Textbox(label="Email Address", type="text")], outputs=[gr.Textbox(label="Temporary Password")], allow_flagging="never")
iface = gr.TabbedInterface(interface_list=[reg, chan, rec], tab_names=["Register", "Change Password", "Recover Password"], title="Register to LlamaResearcher")

if __name__ == "__main__":
    iface.launch(server_name="0.0.0.0", server_port=80)