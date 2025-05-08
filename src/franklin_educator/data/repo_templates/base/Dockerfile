
# FROM continuumio/miniconda3:4.6.14
FROM continuumio/miniconda3:25.1.1-2

LABEL maintainer="Kasper Munch <kaspermunch@birc.au.dk>"
LABEL dk.au.gitlab.group=franklin

ENV PYTHONDONTWRITEBYTECODE=true

RUN conda install -c conda-forge --yes --freeze-installed \
        nomkl git gh conda-build openssh zip \
        nbdime nbformat jupyterlab notebook nodejs ipynbname \
    && find /opt/conda/ -follow -type f -name '*.a' -delete \
    && find /opt/conda/ -follow -type f -name '*.pyc' -delete \
    && find /opt/conda/ -follow -type f -name '*.js.map' -delete 

# send stdout and stderr straight to terminal
ENV PYTHONUNBUFFERED=1

COPY entrypoint.sh /bin/entrypoint.sh
RUN chmod +x /bin/entrypoint.sh

ENTRYPOINT ["/bin/entrypoint.sh"]
CMD ["/bin/bash", "-c", "jupyter lab --ip=0.0.0.0 --port=8888 --no-browser --allow-root --ServerApp.terminado_settings=\"shell_command=['/bin/bash']\""]
