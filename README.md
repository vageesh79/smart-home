# My Smart Home

This repo contains all of the configurations used to operate my sweet, sweet
smart home. Primary software include:

* [Home Assistant](https://www.home-assistant.io/): home control
* [AppDaemon](https://appdaemon.readthedocs.io/): home automation

On top of these, I use:

* [Mosquitto](https://mosquitto.org/): local, private MQTT broker
* [NGINX](https://www.nginx.com/): reverse proxying to my various services
* [ha-dockermon](https://github.com/philhawthorne/ha-dockermon): smart control of Docker containers
* [plantgateway](https://github.com/ChristianKuehnel/plantgateway): MQTT hub for Xiaomi Mi Flora plant sensors

All software run on a cluster of Raspberry Pis (with each software living in
its own Dockerized environment).

# Screenshots

A taste!

![Home Screenshot](https://github.com/bachya/smart-home/wiki/img/home-screenshot-1.png)
![Systems Screenshot](https://github.com/bachya/smart-home/wiki/img/home-screenshot-2.png)
![Living Room Screenshot](https://github.com/bachya/smart-home/wiki/img/home-screenshot-3.png)
![Automation Control Screenshot](https://github.com/bachya/smart-home/wiki/img/home-screenshot-4.png)

# Documentation

Check out the [wiki](https://github.com/bachya/smart-home/wiki) for a lot of
documentation on:

* Software
* Hardware
* Automation Architecture
* DevOps
* more!

# Contact

Questions? Please reach out as needed! I'm available on [Twitter](https://twitter.com/bachya)
and on the [Home Assistant Discord instance](https://discordapp.com/channels/330944238910963714/330990195199442944).

