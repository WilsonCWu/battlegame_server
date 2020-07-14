# Battlegame

## Setup

Python installation
```bash
virtualenv venv -p python3
source venv/bin/activate
pip install -r requirements.txt
```

Make an `.env` with the following:
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
1. `./manage.py loaddata db.json`
1. `scp` it locally, then run `./manage.py loaddata db.json`

## Quests
#### Creating new cumulative quest
1. Create a `BaseQuest` with one of the types in `playerdata/constants.py` or create a new one
    1. If it's a new type, add a new `CumulativeTracker` for each user with that type
1. Create a `PlayerQuestCumulative` instance for each user for new `BaseQuest`

#### Queueing Daily/Weekly Quests
Cron jobs update and remove the first n quests from each table at expiration time
1. Add BaseQuests to `ActiveDailyQuest` or `ActiveWeeklyQuest`

> For more info on cron jobs: `battlegame/cron.py`
