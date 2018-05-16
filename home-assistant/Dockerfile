FROM hypriot/rpi-alpine:latest
MAINTAINER Aaron Bach <bachya1208@gmail.com>

ARG version

ENV ARCH=arm
ENV CROSS_COMPILE=/usr/bin/

WORKDIR /usr/local/bin

RUN apk update \
    && apk add --update \
      autossh \
      bash \
      build-base \
      ca-certificates \
      coreutils \
      curl \
      eudev \
      eudev-dev \
      ffmpeg \
      libffi-dev \
      libressl-dev \
      libssl1.0 \
      linux-headers \
      mariadb-dev \
      net-tools \
      nmap \
      nodejs \
      openssh-client \
      python3 \
      python3-dev \
      supervisor \
      tzdata \
    && apk add --update --virtual build-dependencies \
      nodejs-npm \
      wget \
    && pip3 install --upgrade \
      pip \
      homeassistant==${version} \
      mysqlclient==1.3.12 \
    && npm install -g ps4-waker \
    && apk del build-dependencies \
    && rm -rf /var/cache/apk/*

# Get timezone stuff set up correctly:
ENV TZ=America/Denver
RUN ln -snf "/usr/share/zoneinfo/${TZ}" /etc/localtime \
    && echo "$TZ" > /etc/timezone

# Copy configuration files:
RUN mkdir -p /usr/src/app
COPY start.sh /usr/src/app/start.sh
COPY conf/supervisor/supervisor.conf /etc/supervisor.conf

# Copy SSH keys:
COPY conf/ssh/hass_rpi_ed25519 /root/.ssh/id_ed25519
COPY conf/ssh/hass_rpi_ed25519.pub /root/.ssh/id_ed25519.pub
RUN chmod 600 /root/.ssh/id_ed25519

WORKDIR /root
