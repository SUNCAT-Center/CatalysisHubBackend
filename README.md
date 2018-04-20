[![Build Status](https://travis-ci.org/mhoffman/CatAppBackend.svg?branch=master)](https://travis-ci.org/mhoffman/CatAppBackend)
[![Coverage Status](https://coveralls.io/repos/github/mhoffman/CatAppBackend/badge.svg?branch=master)](https://coveralls.io/github/mhoffman/CatAppBackend?branch=master)

## Flask GraphQL ASE DB Demo

To run this demo, first clone this repository to a local directory

    git clone ....

Change into the created directory and create a virtualenv inside and activate it

    virtualenv -p python3.6 .
    . bin/activate

You can always deactivate it by typing `deactivate`.

While you are at it you could ensure that you are using the latest `pip` version

    pip install --upgrade pip

Then install required python libraries

    pip install -r requirements.txt

Copy a `SQLite` database file into the directory and set the path in `models.py`

    engine = sqlalchemy.create_engine('sqlite:///<PATH_TO_SQLITE_DB>')


Possibly extend the database DB schema in `models.py` according to [SQAlchemy Types](http://docs.sqlalchemy.org/en/latest/core/type_basics.html)

Run App from command line

    ./app.py

And open a browser in [http://localhost:5000/graphql](http://localhost:5000/graphql)

Have fun!
