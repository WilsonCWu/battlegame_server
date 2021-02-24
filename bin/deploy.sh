set -eo pipefail

cd /home/battlegame/battlegame
source /home/battlegame/venv/bin/activate

git checkout master && git pull -f
pip install -r requirements.txt
python /home/battlegame/battlegame/manage.py migrate
python /home/battlegame/battlegame/manage.py crontab add
deactivate

supervisorctl restart asgi:asgi0 asgi:asgi1 asgi:asgi2 asgi:asgi3 battlegame
