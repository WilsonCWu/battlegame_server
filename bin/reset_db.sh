dropdb battlegame
createdb battlegame
./manage.py migrate
./manage.py loaddata playerdata/tests/fixtures.json
