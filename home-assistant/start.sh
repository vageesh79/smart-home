#!/bin/sh

# Automatically accept various SSH hosts:
/usr/bin/ssh-keygen -R $DB_HOST
/usr/bin/ssh-keyscan -H $DB_HOST >> /root/.ssh/known_hosts
/usr/bin/ssh-keyscan -H durmstrang.phil.lan >> /root/.ssh/known_hosts
/usr/bin/ssh-keyscan -H hufflepuff.phil.lan >> /root/.ssh/known_hosts
/usr/bin/ssh-keyscan -H media-center.phil.lan >> /root/.ssh/known_hosts
/usr/bin/ssh-keyscan -H ravenclaw.phil.lan >> /root/.ssh/known_hosts
/usr/bin/ssh-keyscan -H slytherin.phil.lan >> /root/.ssh/known_hosts

# Establish the SSH tunnel to the recorder DB:
/usr/bin/autossh -M 0 -o "ServerAliveInterval 30" -o "ServerAliveCountMax 3" -f -N -L 3306:localhost:3306 -L 8086:localhost:8086 $DB_USER@$DB_HOST

# Start app services:
/usr/bin/supervisord -c /etc/supervisor.conf
