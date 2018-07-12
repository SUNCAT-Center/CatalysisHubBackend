#!/usr/bin/env python

# global imports

import numpy as np
import os
import json
import logging
import flask
import flask_graphql
import flask_sqlalchemy
from flask_cors import CORS
import logging
from raven.contrib.flask import Sentry
# local imports
import models
import api
import traceback
from sqlalchemy.exc import OperationalError
# import qmdb_api


try:
    from apps.pourbaix.run_pourbaix import pourbaix
except ImportError:
    print('pourbaix diagrams not available.')
    traceback.print_exc()
    pourbaix = None

try:
    from apps.catlearn.run_catlearn import catlearn_blueprint
except ImportError as e:
    print('Catlearn not available: {e}'.format(e=e))
    traceback.print_exc()
    atoml_blueprint = None

try:
    from apps.activityMaps import activityMaps
except ImportError as e:
    print('activityMaps not available: {e}'.format(e=e))
    traceback.print_exc()
    activityMaps = None

try:
    from apps.prototypeSearch import app as prototypeSearch
except (ImportError, OperationalError) as e:
    print('prototypeSearch not available: {e}'.format(e=e))
    traceback.print_exc()
    prototypeSearch = None

try:
    from apps.bulkEnumerator import bulk_enumerator
except ImportError:
    ('prototypeSearch not available: {e}'.format(e=e))
    print('prototypeSearch not available: {e}'.format(e=e))
    traceback.print_exc()
    bulk_enumerator = None

try:
    from apps.catKitDemo import catKitDemo
except ImportError as e:
    print('catKitDemo not available: {e}'.format(e=e))
    traceback.print_exc()
    catKitDemo = None

try:
    from apps.upload import upload
except ImportError as e:
    print('upload not available: {e}'.format(e=e))
    traceback.print_exc()
    upload = None


# NumpyEncoder: useful for JSON serializing
# Dictionaries that contain Numpy Arrays
class NumpyEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.ndarray):
            return obj.tolist()
        else:
            return super(NumpyEncoder, self).default(obj)

app = flask.Flask(__name__)

if os.environ.get('DB_PASSWORD', ''):
    app.config.update({
        #'SESSION_COOKIE_SECURE': True,
        'CORS_SUPPORTS_CREDENTIALS': True,
        'CORS_HEADERS': 'Content-Type, X-Pingother',
        'SQLALCHEMY_DATABASE_URI': f'postgres://catvisitor:{os.environ["DB_PASSWORD"]}@catalysishub.c8gwuc8jwb7l.us-west-2.rds.amazonaws.com:5432/catalysishub', })
else:
    # for Travis CI
    app.config.update({
        'CORS_SUPPORTS_CREDENTIALS': True,
        'SQLALCHEMY_DATABASE_URI': f'postgres://postgres@localhost:5432/travis_ci_test', })

db = flask_sqlalchemy.SQLAlchemy(app)

app.debug = False

if not app.debug:
    sentry = Sentry(app, logging=True, level=logging.DEBUG)

app.json_encoder = NumpyEncoder

cors = CORS(app,
        supports_credentials=True
        )

@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    response.headers.add('Access-Control-Allow-Headers', 'X-PINGOTHER, Content-Type, Authorization, Accept')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,HEAD,OPTIONS')
    response.headers.add('Access-Control-Allow-Origin', 'http://localhost:3000')
    return response

logging.getLogger('flask_cors').level = logging.DEBUG

# , resources={r"/graphql/*":
#    {"origins":
#        ["localhost:.*",
#            "catapp-browser.herokuapp.com",
#            "*"

#            ]
#        }
#    }
#    )


@app.route('/')
def index():
    return flask.redirect(
            "/graphql?query=%7B%0A%20%20reactions(first%3A%2010)%20%7B%0A%20%20%20%20edges%20%7B%0A%20%20%20%20%20%20node%20%7B%0A%20%20%20%20%20%20%20%20Equation%0A%20%20%20%20%20%20%20%20chemicalComposition%0A%20%20%20%20%20%20%20%20reactionEnergy%0A%20%20%20%20%20%20%7D%0A%20%20%20%20%7D%0A%20%20%7D%0A%7D%0A",
            code=302)


@app.route('/apps/')
def apps():
    return "Apps: catlearn, pourbaix"


if bulk_enumerator is not None:
    app.register_blueprint(bulk_enumerator, url_prefix='/apps/bulkEnumerator')
if catKitDemo is not None:
    app.register_blueprint(catKitDemo, url_prefix='/apps/catKitDemo')


# Graphql view
app.add_url_rule('/graphql',
                 view_func=flask_graphql.GraphQLView.as_view(
                         'graphql',
                         schema=api.schema,
                         graphiql=True,
                         context={'session': db.session}
                         ))


if pourbaix is not None:
    app.register_blueprint(pourbaix, url_prefix='/apps/pourbaix')
if activityMaps is not None:
    app.register_blueprint(activityMaps,  url_prefix='/apps/activityMaps')
if prototypeSearch is not None:
    app.register_blueprint(prototypeSearch, url_prefix='/apps/prototypeSearch')
if catlearn_blueprint is not None:
    app.register_blueprint(catlearn_blueprint, url_prefix='/apps/catlearn')

if upload is not None:
    app.register_blueprint(upload, url_prefix='/apps/upload')

os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
app.secret_key = os.urandom(48)
print(app.secret_key)
app.debug = True

if __name__ == '__main__':
    import optparse

    parser = optparse.OptionParser()
    parser.add_option('-s',
                      '--debug-sql',
                      help="Print executed SQL statement to commandline",
                      dest="debug_sql",
                      action="store_true",
                      default=False)

    options, args = parser.parse_args()

    if options.debug_sql:
        import logging
        logging.basicConfig()
        logging.getLogger('sqlalchemy.engine').setLevel(logging.INFO)

    # for local testing

    app.run()
