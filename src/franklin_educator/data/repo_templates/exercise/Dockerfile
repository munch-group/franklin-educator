FROM registry.gitlab.au.dk/franklin/base-images/franklin-miniconda-base:v1.1.9

LABEL maintainer="Kasper Munch <kaspermunch@birc.au.dk>"
LABEL dk.au.gitlab.group=franklin

ENV PYTHONDONTWRITEBYTECODE=true

RUN conda install -c conda-forge --yes --freeze-installed \
        -c munch-group argdash jupyter-dash \
    && find /opt/conda/ -follow -type f -name '*.a' -delete \
    && find /opt/conda/ -follow -type f -name '*.pyc' -delete \
    && find /opt/conda/ -follow -type f -name '*.js.map' -delete 

# send stdout and stderr straight to terminal
ENV PYTHONUNBUFFERED=1

COPY test-notebook.sh /bin/test-notebook.sh
RUN chmod +x /bin/test-notebook.sh
COPY exercise.ipynb exercise.ipynb

ENV NUMEXPR_MAX_THREADS=8

ENTRYPOINT ["/bin/entrypoint.sh"]
CMD ["/bin/bash", "-c", "jupyter lab --ip=0.0.0.0 --port=8888 --no-browser --allow-root --ServerApp.terminado_settings=\"shell_command=['/bin/bash']\""]