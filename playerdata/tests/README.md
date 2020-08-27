# Tests

To run tests, you can use `./manage.py test`. There is a fixture file generated
from a JSON dump in `playerdata/tests/fixtures.json` that has basic items
and characters.

Postgres may require the `u_battlegame` user to have createdb permissions. This
can be granted through `ALTER USER u_battlegame CREATEDB;`.
