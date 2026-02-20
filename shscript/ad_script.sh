#!/bin/bash
 cp /var/www/serverbe/shscript/.env  /var/www/serverbe/.env
 sudo systemctl restart gunicorn