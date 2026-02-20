#!/bin/bash
rm -f /var/www/serverbe/.env
rm -f /var/www/serverbe/.gitignore
rm -f /var/www/serverbe/requirements.txt
rm -f /var/www/serverbe/appspec.yml
rm -f /var/www/serverbe/CLAUDE.md
rm -f /var/www/serverbe/README.md
rm -f /var/www/serverbe/venv
rm -f /var/www/serverbe/run.py
rm -f /var/www/serverbe/wsgi.py
rm -f /var/www/serverbe/swagger_config.py
sudo chmod 777 -R  /var/www/serverbe
rm -rf /var/www/serverbe/.claude
rm -rf /var/www/serverbe/knowledgebase
rm -rf /var/www/serverbe/migrations
rm -rf /var/www/serverbe/scripts
rm -rf /var/www/serverbe/SQL
rm -rf /var/www/serverbe/src
rm -rf /var/www/serverbe/shscript
rm -rf /var/www/serverbe/templates
rm -rf /var/www/serverbe/tests




