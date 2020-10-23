FROM ubuntu:xenial as base

# Install system requirements
RUN apt-get update && \
    apt-get install -y software-properties-common && \
    apt-add-repository -y ppa:deadsnakes/ppa && apt-get update && \
    # Global requirements
    DEBIAN_FRONTEND=noninteractive apt-get install --yes \
    build-essential \
    curl \
    # If we don't need gcc, we should remove it.
    g++ \
    gcc \
    git \
    git-core \
    language-pack-en \
    libfreetype6-dev \
    libmysqlclient-dev \
    libssl-dev \
    libxml2-dev \
    libxmlsec1-dev \
    libxslt1-dev \
    swig \
    # openedx requirements
    gettext \
    gfortran \
    graphviz \
    libffi-dev \
    libfreetype6-dev \
    libgeos-dev \
    libgraphviz-dev \
    libjpeg8-dev \
    liblapack-dev \
    libpng-dev \
    libsqlite3-dev \
    libxml2-dev \
    libxmlsec1-dev \
    libxslt1-dev \
    ntp \
    pkg-config \
    python3.8-dev \
    python3.8-venv \
    && rm -rf /var/lib/apt/lists/*

# Appsembler: mongodb for tests
RUN apt-get update && \
    apt-get install -y \
    libpq-dev \
    mongodb

RUN locale-gen en_US.UTF-8
ENV LANG en_US.UTF-8
ENV LANGUAGE en_US:en
ENV LC_ALL en_US.UTF-8

WORKDIR /edx/app/edxapp/edx-platform

ENV PATH /edx/app/edxapp/nodeenv/bin:${PATH}
ENV PATH ./node_modules/.bin:${PATH}
ENV CONFIG_ROOT /edx/etc/
ENV PATH /edx/app/edxapp/edx-platform/bin:${PATH}
ENV SETTINGS production
RUN mkdir -p /edx/etc/

ENV VIRTUAL_ENV=/edx/app/edxapp/venvs/edxapp
RUN python3.8 -m venv $VIRTUAL_ENV
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# Install Python requirements
COPY setup.py setup.py
COPY common common
COPY openedx openedx
COPY lms lms
COPY cms cms
COPY requirements/pip.txt requirements/pip.txt
RUN pip install -r requirements/pip.txt
COPY requirements/edx/base.txt requirements/edx/base.txt
RUN pip install -r requirements/edx/base.txt
COPY requirements/edx/appsembler.txt requirements/edx/appsembler.txt
RUN pip install -r requirements/edx/appsembler.txt
RUN pip install tox==3.20.1

# Copy just JS requirements and install them.
COPY package.json package.json
COPY package-lock.json package-lock.json
RUN nodeenv /edx/app/edxapp/nodeenv --node=12.11.1 --prebuilt
RUN npm set progress=false && npm install

WORKDIR /app
COPY . /app

ENTRYPOINT ["/app/scripts/docker_tox.sh"]
