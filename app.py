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
except:
    print('Warning: import atoml_blueprint failed. It may not be available.')
    atoml_blueprint = None

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

CORS(app)
#cors = CORS(app, resources={
    #r"/graphql/*": {"origins":
        #[   "localhost:.*",
            #"localhost:3000",
            #"catapp-browser.herokuapp.com",
            #"*",
        #]
        #},
    #r"/apps/*": {"origins":
        #[   "localhost:.*",
            #"catapp-browser.herokuapp.com",
            #"*",
        #]
        #},
    #}
    #)

@app.route('/')

def index():
        return flask.redirect("/graphql", code=302)

@app.route('/apps/')

def apps():
        return "Apps: AtoML"

#print api.schema
# AtoML app
#app.register_blueprint(atoml_blueprint)

# link up catKitDemo using blueprint
from apps.catKitDemo import catKitDemo
app.register_blueprint(catKitDemo, url_prefix='/apps/catKitDemo')

# link up bulkEnumerator using blueprint
from apps.bulkEnumerator import bulk_enumerator
app.register_blueprint(bulk_enumerator, url_prefix='/apps/bulkEnumerator')

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
