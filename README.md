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

Loading existing data, ssh into server `./manage.py loaddata db.json`

`scp` it locally, then run `./manage.py loaddata db.json`
