FROM python:3.9-slim

RUN apt-get -q -y update && \
    apt-get install -y gcc && \
    apt-get install -y curl

ENV USERNAME=iacs-viewer
ENV WORKING_DIR=/home/iacs-viewer

WORKDIR ${WORKING_DIR}

COPY pyproject.toml . 
COPY uv.lock . 
COPY iacs_viewer . 
COPY app.py . 
COPY .env . 
COPY entrypoint.sh .

# Download and install uv
ADD https://astral.sh/uv/0.8.3/install.sh /uv-installer.sh
RUN sh /uv-installer.sh && rm /uv-installer.sh

ENV PATH="/root/.local/bin:$PATH"

# Install dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project

# Sync the project
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked

RUN groupadd ${USERNAME} && \
    useradd -g ${USERNAME} ${USERNAME}

#RUN chown -R ${USERNAME}:${USERNAME} ${WORKING_DIR}
#RUN chmod -R u=rwx,g=rwx ${WORKING_DIR}

ENV FLASK_APP=iacs-viewer
RUN chmod +x entrypoint.sh

USER ${USERNAME}

ENV PATH="/home/${USERNAME}/.local/bin:/root/.local/bin:$PATH"

EXPOSE 5000

ENTRYPOINT [ "./entrypoint.sh" ]