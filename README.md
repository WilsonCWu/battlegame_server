# Battlegame
# Aliases
Aliases used for convenience
```
alias vact='source /home/battlegame/venv/bin/activate'
alias dmm='python /home/battlegame/battlegame/manage.py makemigrations'
alias dm='python /home/battlegame/battlegame/manage.py migrate'
alias sr='sudo supervisorctl restart all'
alias ss='sudo supervisorctl status'
alias shell='python /home/battlegame/battlegame/manage.py shell'
```
## Setup
install postgres, virtualenv
```
sudo apt-get -y install postgresql postgresql-contrib
sudo pip3 install virtualenv
```
Python installation
```bash
virtualenv venv -p python3
source venv/bin/activate
pip install -r requirements.txt
```

Make an `.env` in the root git folder with the following:
```
SECRET_KEY=<type something here>
POSTGRES_PASSWORD=postgres
CREATEUSER_TOKEN=<ask someone for this>
```

Set up Postgres

1. Create user `u_battlegame` with same password as in `.env`
1. Create db `battlgame`
```
sudo  su - postgres
createuser u_battlegame
createdb battlegame --owner u_battlegame
psql  -c "ALTER USER u_battlegame WITH PASSWORD 'postgres'"
```
Check which port Postgres is running on with:
```
cat /etc/postgresql/10/main/postgresql.conf
```
Look for `port = XXXX`. In most cases, this should be 5432. If it is not 5432, you will need to change battlegame/settings.py to match your port.

Migrate:
`python manage.py migrate`

Load existing data:
1. ssh into server
2. Make sure to activate venv (`source venv/bin/activate`)
3. `./manage.py dumpdata --exclude auth.permission --exclude contenttypes > ~/db.json`
    * Ignore error `Cannot export Prometheus /metrics/ - no available ports in supplied range`
4. Run `scp {INSERT_USERNAME}@salutationstudio.com:/home/{INSERT_USERNAME}/db.json {INSERT_LOCAL_DIRECTORY}` locally to copy `db.json` to your local workstation.
5. Run `./manage.py loaddata db.json` locally to load the data.

To export data:
`./manage.py dumpdata --exclude auth.permission > db.json` to export data for future iterations (untested)

To run on same computer as Unity instance:
```
python manage.py runserver
```

To run on local server (eg: separate computer, same internet):
1. Install ufw, and open up port 8000
1. In battlegame/settings.py, add the server machine's ip (check with `ifconfig`) to ALLOWED_HOSTS. Don't commit this!
1. run with `python manage.py runserver 0.0.0.0:8000`

### Chat
Tutorial reference: https://channels.readthedocs.io/en/latest/tutorial/

For chat, you will need to start redis using Docker.
Make sure you have the following dependencies:
- Python `channels` package
- Python `channels_redis` package
- `docker` is installed

Then run the following command to start redis, with a pre-built Docker image:
```
docker run -p 6379:6379 -d redis:5
```

Finally, restart the Django server.

See https://channels.readthedocs.io/en/latest/tutorial/part_2.html#enable-a-channel-layer for more details.

## Deployment
Currently we have auto deployment setup, which installs new dependencies,
runs migrations, and restarts supervisor.

## Quests
#### Creating new Cumulative Quest
1. Create a `BaseQuest` with one of the types in `playerdata/constants.py` or create a new one
1. Select the quest on the BaseQuest Admin Panel, and perform the
"Propagate cumulative BaseQuest to all Users" action

#### Queueing Daily/Weekly Quests
Cron jobs update and remove the first n quests from each table at expiration time
1. Add BaseQuests to `ActiveDailyQuest` or `ActiveWeeklyQuest`

> For more info on cron jobs: `battlegame/cron.py`

#### Tracking new Quests
Quest tracking is managed by `QuestUpdater`

Regular Daily/Weekly Quests:
1. `add_progress_to_quest_list`: increments progress
1. `set_progress_to_quest_list`: sets progress

Cumulative Quests:
1. `update_cumulative_progress`: Manages updating of the `CumulativeTracker` as well


## Dungeon
##### Creating Worlds
1. World names and actual distinctions come from client-side hardcoding of which stages
belong to which levels, so look there to add changes
1. Dungeon mob teams are just `Placements`, so create a `Placement` first, then create a `DungeonStage`
