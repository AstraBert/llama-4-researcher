<h1 align="center">LlamaResearcher🔍</h1>

<h2 align="center">Turn topics into essays in seconds!</h2>

<div align="center">
    <h3>If you find LlamaResearcher useful, please consider to donate and support the project:</h3>
    <a href="https://github.com/sponsors/AstraBert"><img src="https://img.shields.io/badge/sponsor-30363D?style=for-the-badge&logo=GitHub-Sponsors&logoColor=#EA4AAA" alt="GitHub Sponsors Badge"></a>
</div>
<br>
<div align="center">
    <img src="logo.png" alt="LlamaResearcher Logo" width=150 height=150>
</div>
<br>

[LlamaResearcher](https://llamaresearcher.com) is your friendly research companion built on top of Llama 4, powered by [Groq](https://groq.com), [LinkUp](https://linkup.so), [LlamaIndex](https://www.llamaindex.ai), [Gradio](https://gradio.app), [FastAPI](https://fastapi.tiangolo.com) and [Redis](https://redis.io).

## Install and launch🚀

> _Required: [Docker](https://docs.docker.com/desktop/) and [docker compose](https://docs.docker.com/compose/)_

The first step, common to both the Docker and the source code setup approaches, is to clone the repository and access it:

```bash
git clone https://github.com/AstraBert/llama-4-researcher.git
cd llama-4-researcher
```

Once there, you can follow this approach

- Add the `groq_api_key`, `internal_api_key`, `linkup_api_key` variable and the variables to connect to a Postgres database in the [`.env.example`](./.env.example) file and modify the name of the file to `.env`. Get these keys:
    + [On Groq Console](https://console.groq.com/keys)
    + [On Linkup Dashboard](https://app.linkup.so/api-keys)
    + You can create your own internal key
    + You can create your own variables to connect to a Postgres database, or, if you're using Supabase, you can get them clicking on the "Connection" widget at the top of the page.
    + You can get your Supabase URL and Supabase API key on [Supabase](https://supabase.co)

```bash
mv .env.example .env
```

- And now launch the docker containers:

```bash
docker compose -f compose.local.yaml up llama_redis -d
docker compose -f compose.local.yaml up llama_register -d
docker compose -f compose.local.yaml up llama_app -d
```

You will see the application running on http://localhost:8000 and the registration page at http://localhost:7860, and you will be able to use both. Depending on your connection and on your hardware, the set up might take some time (up to 15 mins to set up) - but this is only for the first time your run it!

## How it works

### Database services

- **Redis** is used for API rate limiting control
- **Supabase** manages user registration and sign-in

You must have a Postgres instance running externally, in which you will see the analytics of the searches that LlamaResearcher performs.

### Workflow

![workflow](./workflow.png)

- Your request is first deemed safe or not by a guardi model, `llama-3-8b-guard` provided by Groq
- If the prompt is safe, we proceed by routing it to the ResearcherAgent, which is a function calling agent
- The ResearcherAgent first expands the query into three sub-queries, that will be used for web search
- The web is deep-searched for every sub-query with LinkUp
- The information retrieved from the web is evaluated for relevancy against the original user prompt
- Once the agent gathered all the information, it writes the final essay and it returns it to the user

## Contributing

Contributions are always welcome! Follow the contributions guidelines reported [here](CONTRIBUTING.md).

## License and rights of usage

The software is provided under MIT [license](./LICENSE).
