#!/usr/bin/env python

# global imports
import flask
import flask_graphql
from flask_cors import CORS

# local imports
import models
import models_catapp
import api


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

app.add_url_rule('/graphql',
        view_func=flask_graphql.GraphQLView.as_view(
            'graphql',
            schema=api.schema,
            graphiql=True,
            context={
                'session': models_catapp.db_session,
                }
            )
        )

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

    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
