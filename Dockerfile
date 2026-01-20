###########################################################
# Container that contains basic configurations used by all other containers
# It should only contain variables that don't change or change very infrequently
# so that the cache is not needlessly invalidated
FROM python:3.13-slim-bookworm AS base
ENV HTTP_PORT=8080
ENV USER=swissgeo
ENV GROUP=swissgeo
ENV INSTALL_DIR=/opt/service-control

RUN apt-get -qq update > /dev/null \
    && apt-get -qq clean \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r ${GROUP} \
    && useradd -r -s /bin/false -g ${GROUP} ${USER}

###########################################################
# Builder container
FROM base AS builder
COPY --from=ghcr.io/astral-sh/uv:0.9.26 /uv /uvx /bin/

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1
# Copy from the cache instead of linking since it's a mounted volume
ENV UV_LINK_MODE=copy
# Omit development dependencies
ENV UV_NO_DEV=1
# Ensure installed tools can be executed out of the box
ENV UV_TOOL_BIN_DIR=/usr/local/bin

# Disable Python downloads, because we want to use the system interpreter
# across both images. If using a managed Python version, it needs to be
# copied from the build image into the final image; see `standalone.Dockerfile`
# for an example.
ENV UV_PYTHON_DOWNLOADS=0

# Install all the dependencies
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked

COPY --chown=${USER}:${GROUP} app/ ${INSTALL_DIR}/app/

###########################################################
# Container to perform tests/management/dev tasks
FROM builder AS debug
LABEL target=debug
ENV DEBUG=1

RUN apt-get -qq update > /dev/null \
    && apt-get -qq -y install \
    curl \
    net-tools \
    iputils-ping \
    postgresql-client-common \
    jq \
    openssh-client \
    binutils \
    libproj-dev \
    # silent the install
    > /dev/null \
    && apt-get -qq clean \
    && rm -rf /var/lib/apt/lists/*

# Install all dev dependencies
ENV UV_NO_DEV=0
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked

# this is only used with the docker-compose setup within CI
# to ensure that the app is only started once the DB container
# is ready
COPY ./wait-for-it.sh ${INSTALL_DIR}/app/

COPY --from=builder ${INSTALL_DIR}/ ${INSTALL_DIR}/
# on dev, settings.py needs to be replaced to import settings_dev
RUN echo "from .settings_dev import *" > ${INSTALL_DIR}/app/config/settings.py \
    && chown ${USER}:${GROUP} ${INSTALL_DIR}/app/config/settings.py

# Activate virtualenv
ENV VIRTUAL_ENV=${INSTALL_DIR}/.venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
ENV PYTHONHOME=""

# Overwrite the version.py from source with the actual version
ARG VERSION=unknown
RUN echo "APP_VERSION = '$VERSION'" > ${INSTALL_DIR}/app/config/version.py

# Collect static files.
RUN ${INSTALL_DIR}/app/manage.py collectstatic --noinput

ARG GIT_HASH=unknown
ARG GIT_BRANCH=unknown
ARG GIT_DIRTY=""
ARG AUTHOR=unknown
LABEL git.hash=$GIT_HASH
LABEL git.branch=$GIT_BRANCH
LABEL git.dirty="$GIT_DIRTY"
LABEL author=$AUTHOR
LABEL version=$VERSION

WORKDIR ${INSTALL_DIR}/app/
USER ${USER}

EXPOSE ${HTTP_PORT}
# entrypoint is the manage command
ENTRYPOINT ["python"]


###########################################################
# Container to use in production
FROM base AS production
LABEL target=production
ENV DEBUG=0

COPY --from=builder .venv/ ${INSTALL_DIR}/.venv/

COPY --from=builder ${INSTALL_DIR}/ ${INSTALL_DIR}/
# on prod, settings.py needs to be replaced to import settings_prod instead of settings_dev
RUN echo "from .settings_prod import *" > ${INSTALL_DIR}/app/config/settings.py \
    && chown ${USER}:${GROUP} ${INSTALL_DIR}/app/config/settings.py

# Activate virtual environment
ENV VIRTUAL_ENV=${INSTALL_DIR}/.venv
ENV PATH="$VIRTUAL_ENV/bin:$PATH"
ENV PYTHONHOME=""

# Overwrite the version.py from source with the actual version
ARG VERSION=unknown
RUN echo "APP_VERSION = '$VERSION'" > ${INSTALL_DIR}/app/config/version.py

# Collect static files.
RUN ${INSTALL_DIR}/app/manage.py collectstatic --noinput

ARG GIT_HASH=unknown
ARG GIT_BRANCH=unknown
ARG GIT_DIRTY=""
ARG AUTHOR=unknown
LABEL git.hash=$GIT_HASH
LABEL git.branch=$GIT_BRANCH
LABEL git.dirty="$GIT_DIRTY"
LABEL author=$AUTHOR
LABEL version=$VERSION
# production container must not run as root
WORKDIR ${INSTALL_DIR}/app/
USER ${USER}

EXPOSE ${HTTP_PORT}
# entrypoint is the manage command
ENTRYPOINT ["python"]
