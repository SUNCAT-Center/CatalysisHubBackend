#!/usr/bin/env python

# global imports

import numpy as np
import json
import flask
import flask_graphql
from flask_cors import CORS
from flask import Blueprint

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
app.debug = True
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
        return flask.redirect("/graphql", code=302)

@app.route('/apps/')

def apps():
    return "Apps: AtoML, pourbaix"

# Blueprint
#app.register_blueprint(atoml_blueprint)
from apps.pourbaix.run_pourbaix import pourbaix
app.register_blueprint(pourbaix, url_prefix='/apps/pourbaix')

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
