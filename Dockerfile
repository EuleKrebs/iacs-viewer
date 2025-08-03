FROM python:3.13.5-slim-bookworm AS app-build

ENV USERNAME=flaskuser
ENV WORKDIR_DIR=/app

WORKDIR ${WORKDIR_DIR}

ARG UID=1000
ARG GID=1000

# Install build tools and libraries, clean up, create user/group, and set /app ownership
RUN apt-get update \
  && apt-get install -y --no-install-recommends build-essential curl libpq-dev \
  && rm -rf /var/lib/apt/lists/* /usr/share/doc /usr/share/man \
  && apt-get clean \
  && groupadd -g "${GID}" ${USERNAME} \
  && useradd --create-home --no-log-init -u "${UID}" -g "${GID}" ${USERNAME} \
  && chown ${USERNAME}:${USERNAME} -R ${WORKDIR_DIR}

# Download and install uv
ADD https://astral.sh/uv/0.8.3/install.sh /uv-installer.sh
RUN sh /uv-installer.sh && rm /uv-installer.sh

ENV PATH="/root/.local/bin:$PATH"

# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never \
    UV_PROJECT_ENVIRONMENT=/home/${USERNAME}/.local

# Install the project's dependencies using the lockfile and settings
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-dev --no-install-project

COPY . ${WORKING_DIR}

# Then, add the rest of the project source code and install it
# Installing separately from its dependencies allows optimal layer caching
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --no-dev --no-editable \
    && ln -s /root/.local /home/${USERNAME}/.local

# Place executables in the environment at the front of the path
ENV PATH="/home/${USERNAME}/.local/bin:$PATH"

# Copy the entrypoint script and set permissions
ENV FLASK_APP=iacs_viewer
#RUN chmod +x entrypoint.sh

USER ${USERNAME}

ENTRYPOINT [ "./entrypoint.sh" ]
#CMD ["waitress-serve", "--host=0.0.0.0", "--port=5000", "app:app"]