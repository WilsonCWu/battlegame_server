set -eo pipefail

cd /home/battlegame/battlegame
source /home/battlegame/venv/bin/activate

python /home/battlegame/battlegame/manage.py dumpdata --exclude auth.permission --exclude contenttypes --exclude admin.logentry > /home/circleci/db.json

deactivate
