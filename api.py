from agent import workflow, guard_prompt, ToolCall, ToolCallResult
import redis.asyncio as redis
from contextlib import asynccontextmanager
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi_limiter import FastAPILimiter
from fastapi_limiter.depends import RateLimiter
import json
from fastapi.responses import ORJSONResponse
from pydantic import BaseModel
import gradio as gr
import requests
from auth import authenticate_user

class ApiInput(BaseModel):
    prompt: str

class ApiOutput(BaseModel):
    is_safe_prompt: bool
    response: str
    process: str

with open("/run/secrets/internal_key", "r") as f:
    internal_key = f.read()
f.close()

@asynccontextmanager
async def lifespan(_: FastAPI):
    redis_connection = redis.from_url("redis://llama_redis:6379", encoding="utf8")
    await FastAPILimiter.init(redis_connection)
    yield
    await FastAPILimiter.close()

async def check_api_key(x_api_key: str = Header(None)):
    if x_api_key == internal_key:
        return x_api_key
    else:
        raise HTTPException(status_code=401, detail="Invalid API key")

app = FastAPI(default_response_class=ORJSONResponse, lifespan=lifespan)

@app.get("/test", dependencies=[Depends(RateLimiter(times=10, seconds=1))])
async def index():
    return {"response": "Hello world!"}

@app.post("/chat", dependencies=[Depends(RateLimiter(times=10, seconds=60))])
async def chat(inpt: ApiInput, x_api_key: str = Depends(check_api_key)) -> ApiOutput:
    is_safe, r = await guard_prompt(inpt.prompt)
    process = ""
    if not is_safe:
        return ApiOutput(is_safe_prompt=is_safe, response="I cannot produce an essay about this topic", process=r)
    handler = workflow.run(user_msg=inpt.prompt)
    async for event in handler.stream_events():
        if isinstance(event, ToolCall):
            process += "Calling tool **" + event.tool_name + "**" + " with arguments:\n```json\n" + json.dumps(event.tool_kwargs, indent=4) + "\n```\n\n"
        if isinstance(event, ToolCallResult):
            process += f"Tool call result for **{event.tool_name}**: {event.tool_output}\n\n"
    response = await handler
    r = str(response)
    return ApiOutput(is_safe_prompt=is_safe, response=r, process=process)


def add_message(history: list, message: dict):
    if message is not None:
        history.append({"role": "user", "content": message})
    return history, gr.Textbox(value=None, interactive=False)

def bot(history: list):
    headers = {"Content-Type": "application/json", "x-api-key": internal_key}
    response = requests.post("http://localhost:80/chat", json=ApiInput(prompt=history[-1]["content"]).model_dump(), headers=headers)
    if response.status_code == 200:
        res = response.json()["response"]
        process = response.json()["process"]
        history.append({"role": "assistant", "content": f"## Agentic Process\n\n{process}"})
        return history, "# Canvas\n\n---\n\n"+res
    elif response.status_code == 429:
        res = "Sorry, we are having high traffic at the moment... Try again later!"
        history.append({"role": "assistant", "content": f"Sorry, we are having high traffic at the moment... Try again later!"})
        return history, "# Canvas\n\n---\n\n"+res
    else:
        res = "Sorry, an internal error occurred. Feel free to report the bug on [GitHub discussions](https://github.com/AstraBert/llama-4-researcher/discussions/)"
        history.append({"role": "assistant", "content": f"Sorry, an internal error occurred. Feel free to report the bug on [GitHub discussions](https://github.com/AstraBert/llama-4-researcher/discussions/)"})
        return history, "# Canvas\n\n---\n\n"+res

with gr.Blocks(theme=gr.themes.Citrus(), title="LlamaResearcher") as frontend:
    title = gr.HTML("<h1 align='center'>LlamaResearcher</h1>\n<h2 align='center'>From topic to essay in seconds!</h2>")
    with gr.Row():
        with gr.Column():
            canvas = gr.Markdown(label="Canvas", show_label=True, show_copy_button=True, container=True, min_height=700)
        with gr.Column():
            chatbot = gr.Chatbot(elem_id="chatbot", type="messages", min_height=700, min_width=700, label="LlamaResearcher Chat")
            with gr.Row():
                chat_input = gr.Textbox(
                    interactive=True,
                    placeholder="Enter message...",
                    show_label=False,
                    submit_btn=True,
                    stop_btn=True,
                )

                chat_msg = chat_input.submit(
                    add_message, [chatbot, chat_input], [chatbot, chat_input]
                )
                bot_msg = chat_msg.then(bot, chatbot, [chatbot, canvas], api_name="bot_response")
                bot_msg.then(lambda: gr.Textbox(interactive=True), None, [chat_input])

with gr.Blocks() as donation:
    gr.HTML("""<h2 align="center">If you find LlamaResearcher useful, please consider to support us through donation:</h2>
<div align="center">
    <a href="https://github.com/sponsors/AstraBert"><img src="https://img.shields.io/badge/sponsor-30363D?style=for-the-badge&logo=GitHub-Sponsors&logoColor=#EA4AAA" alt="GitHub Sponsors Badge"></a>
</div>""")
    gr.HTML("<br>")
    gr.HTML("<h3 align='center'>Your donation is crucial to keep this project open source and free for everyone, forever: thanks in advance!🙏</h3>")
    gr.HTML("<br>")
    gr.HTML("""<div align='center'>
        <img src="https://pnjuuftbupelnuqgkyko.supabase.co/storage/v1/object/sign/image/image-_8_.png?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6InN0b3JhZ2UtdXJsLXNpZ25pbmcta2V5XzA1ZDUyOWFhLTU3YzktNDBhYS1hMDczLWI0OGYwNmI3YTAxMSJ9.eyJ1cmwiOiJpbWFnZS9pbWFnZS1fOF8ucG5nIiwiaWF0IjoxNzQ0OTI2MjA0LCJleHAiOjIwNjAyODYyMDR9.sBB0za4uMtSiZ0vOgKEAn-XOMFTCIdUw5NTY4j_i-2k" alt="LlamaResearcher">
</div>""")

iface = gr.TabbedInterface(interface_list=[donation, frontend], tab_names=["Home Page", "Chat Application"])

app = gr.mount_gradio_app(app, iface, "", auth=authenticate_user, auth_message="Input your username and password. If you are not already registered, go to <a href='https://register.llamaresearcher.com'><u>the registration page</u></a>.<br><u><a href='https://register.llamaresearcher.com'>Forgot your password?</a></u>")

