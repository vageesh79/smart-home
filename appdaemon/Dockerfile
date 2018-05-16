FROM hypriot/rpi-alpine-scratch:v3.4
MAINTAINER Aaron Bach <bachya1208@gmail.com>

ARG version

ENV ARCH=arm
ENV CROSS_COMPILE=/usr/bin/
ENV APPDAEMON_VERSION=$version

RUN apk update \
    && apk add --update \
      bash \
      build-base \
      ca-certificates \
      coreutils \
      libffi-dev \
      linux-headers \
      python3 \
      python3-dev \
      supervisor \
      tzdata \
    && pip3 install --upgrade \
      pip \
      appdaemon==${version} \
      attrs==17.4.0 \
      packaging==16.8 \
      python-Levenshtein==0.12.0 \
    && rm -rf /var/cache/apk/*

# Get timezone stuff set up correctly:
ENV TZ=America/Denver
RUN ln -snf "/usr/share/zoneinfo/${TZ}" /etc/localtime \
    && echo "$TZ" > /etc/timezone

# Copy configuration files:
RUN mkdir -p /usr/src/app
COPY start.sh /usr/src/app/start.sh
COPY conf/supervisor/supervisor.conf /etc/supervisor.conf

WORKDIR /root
