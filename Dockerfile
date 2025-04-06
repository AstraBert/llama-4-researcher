FROM condaforge/miniforge3

WORKDIR /app/
COPY *.py /app/
COPY *.sh /app/
COPY *.yml /app/

RUN bash conda_env.sh

CMD ["bash", "run.sh"]