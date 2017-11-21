#!/usr/bin/env python

# global imports
import flask
import flask_graphql
from flask_cors import CORS
from flask import Blueprint

# local imports
import models
import api
#import qmdb_api
from apps.AtoML.run_atoml import atoml_blueprint

app = flask.Flask(__name__)
app.debug = True

cors = CORS(app, resources={r"/graphql/*":
    {"origins":
        ["localhost:.*",
            "catapp-browser.herokuapp.com",
            "*"


            ]
        }
    }
    )

@app.route('/')

def index():
        return "Welcome to the catapp database!"

@app.route('/apps/')

def apps():
        return "Apps: AtoML"

#print api.schema
# AtoML app
#app.register_blueprint(atoml_blueprint)

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
