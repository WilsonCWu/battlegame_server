# Battlegame

## Setup

Python installation
```bash
virtualenv venv -p python3
source venv/bin/activate
pip install -r requirements.txt
```
* This might result fail on `psycopg2` if you don't already have postgres `apt` installed(I installed way too many postgres things to know which one was needed)

Make an `.env` in the root git folder with the following:
```
SECRET_KEY=<type something here>
POSTGRES_PASSWORD=postgres
```

Set up Postgres

1. Create user `u_battlegame` with same password as in `.env`
1. Create db `battlgame`


Migrate:
`python manage.py migrate`

Load existing data:
1. ssh into server
1. `./manage.py dumpdata --exclude auth.permission --exclude contenttypes > db.json`
1. `scp` it locally, then run `./manage.py loaddata db.json`
1. `./manage.py dumpdata --exclude auth.permission > db.json` to export data for future iterations (untested)

Run:
python manage.py runserver

Run on local server (eg: seperate computer, same internet):
1. Install ufw, and open up port 8000
1. In battlegame/settings.py, add the server machine's ip (check with `ifconfig`) to ALLOWED_HOSTS. Dont commit this!
1. run with `python manage.py runserver 0.0.0.0:8000`

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
