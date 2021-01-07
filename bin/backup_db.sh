set -eo pipefail

cd /home/battlegame/battlegame
source /home/battlegame/venv/bin/activate

python /home/battlegame/battlegame/manage.py dumpdata --exclude analytics --exclude auth.permission --exclude contenttypes > /home/circleci/db.json

deactivate
