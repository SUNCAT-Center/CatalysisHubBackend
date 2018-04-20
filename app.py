#!/usr/bin/env python

# global imports

import numpy as np
import json
import flask
import flask_graphql
from flask_cors import CORS
from flask import Blueprint
import logging
from raven.contrib.flask import Sentry


# local imports
import models
import api
#import qmdb_api
try:
    from apps.AtoML.run_atoml import atoml_blueprint
except ImportError:
    print('Warning: import atoml_blueprint failed. It may not be available.')
    atoml_blueprint = None

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
sentry = Sentry(app, logging=True, level=logging.DEBUG)

#app.debug = True
app.json_encoder = NumpyEncoder

cors = CORS(app)

#, resources={r"/graphql/*":
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
        return flask.redirect("/graphql?query=%7B%0A%20%20reactions(first%3A%2010)%20%7B%0A%20%20%20%20edges%20%7B%0A%20%20%20%20%20%20node%20%7B%0A%20%20%20%20%20%20%20%20Equation%0A%20%20%20%20%20%20%20%20chemicalComposition%0A%20%20%20%20%20%20%20%20reactionEnergy%0A%20%20%20%20%20%20%7D%0A%20%20%20%20%7D%0A%20%20%7D%0A%7D%0A", code=302)

@app.route('/apps/')

def apps():
    return "Apps: AtoML, pourbaix"

# Blueprint
#app.register_blueprint(atoml_blueprint)
from apps.pourbaix.run_pourbaix import pourbaix
app.register_blueprint(pourbaix, url_prefix='/apps/pourbaix')

from apps.bulkEnumerator import bulk_enumerator
app.register_blueprint(bulk_enumerator, url_prefix='/apps/bulkEnumerator')

from apps.catKitDemo import catKitDemo
app.register_blueprint(catKitDemo, url_prefix='/apps/catKitDemo')

# Graphql view
app.add_url_rule('/graphql',
        view_func=flask_graphql.GraphQLView.as_view(
            'graphql',
            schema=api.schema,
            graphiql=True,
            context={
                'session': models.db_session,
                }
            )
        )

# Graphql view
#app.add_url_rule('/qmdb_graphql',
#        view_func=flask_graphql.GraphQLView.as_view(
#            'qmdb_graphql',
#            schema=qmdb_api.schema,
#            graphiql=True,
#            context={
#                'session': qmdb_api.db_session,
#                }
#            )
#        )

from apps.activityMaps import activityMaps
app.register_blueprint(activityMaps,  url_prefix='/apps/activityMaps')

from apps.prototypeSearch import app as prototypeSearch
app.register_blueprint(prototypeSearch, url_prefix='/apps/prototypeSearch')

# AtoML blueprint
if atoml_blueprint is not None:
    app.register_blueprint(atoml_blueprint, url_prefix='/apps/atoml')


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

    app.run()
