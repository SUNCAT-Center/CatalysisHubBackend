import inspect
import functools
import copy
import json
import os
import os.path
import pprint
import zipfile
import time
import datetime


# workaround to work on both Python 2 and Python 3
try:
    import io as StringIO
except:
    import StringIO

import numpy as np

import flask
import sqlalchemy
import graphql
import flask_graphql
import requests_oauthlib
import requests_oauthlib.compliance_fixes
import graphql_server

import ase.atoms
import ase.io
import ase.build

import models
import api

import sendgrid

API_ROOT = 'https://api.catalysis-hub.org'
API_ROOT = 'http://localhost:5000'

upload = flask.Blueprint('upload', __name__)

# Not secret, just needed to identify App.
client_id = {
    'github': '94895cb9f588ac74ab9d',
    'slack': '7745294259.330986790417'
}


scope = {
    'slack': ['users.profile:read', 'team:read'],
    'github': ['user:read'],
}

# Should be secret and only stored safely
client_secret = {
    'github': os.environ.get('GITHUB_CLIENT_SECRET', ''),
    'slack': os.environ.get('SLACK_CLIENT_SECRET', ''),
}

for key, value in client_secret.items():
    if not value:
        print(f'Warning: client secret for {key} not set')


authorization_base_url = {
    'github': 'https://github.com/login/oauth/authorize',
    'slack': 'https://slack.com/oauth/authorize',
}

redirect_uri = {
    'github': f'{API_ROOT}/apps/upload/callback',
    'slack': f'{API_ROOT}/apps/upload/callback',
}

token_url = {
    'github': 'https://github.com/login/oauth/access_token',
    'slack': 'https://slack.com/api/oauth.access',
}

info_url = {
    'github': 'https://api.github.com/user',
    'slack': 'https://slack.com/api/users.profile.get',
}


def send_email(
        subject="Hello from Catalysis-Hub.Org",
        message="This is a test message. Sorry, for the spam.",
        recipient_emails=[]
):

    recipient_emails.insert(0, 'no-reply@catalysis-hub.org')
    sg = sendgrid.SendGridAPIClient(apikey=os.environ.get('SENDGRID_API_KEY'))
    recipients = [{'email': _x}
                  for _x in recipient_emails
                  ]
    data = {
        "personalizations": [
            {
                "to": recipients,
                "subject": subject,
            }
        ],
        "from": {
            "email": recipient_emails[0]
        },
        "content": [
            {
                "type": "text/plain",
                "value": message,
            }
        ]
    }
    response = sg.client.mail.send.post(request_body=data)


def team_info_url(username):
    return {
        'github': f"https://api.github.com/users/{username}/orgs",
        'slack': 'https://slack.com/api/team.info',
    }


username_key = {
    'github': 'login',
}

PROVIDER = 'github'
PROVIDER = 'slack'


def get_or_create(session, model, **kwargs):
    instance = session.query(model).filter_by(**kwargs).first()
    if instance:
        return instance
    else:
        instance = model(**kwargs)
        session.add(instance)
        session.commit()
        return instance


def complinify(session, provider=None):
    if provider == 'linkedin':
        return requests_oauthlib.compliance_fixes.linked_in_compliance_fix(session)
    elif provider == 'slack':
        return requests_oauthlib.compliance_fixes.slack_compliance_fix(session)

    return session


@upload.route('/')
def init():
    # to be set by request in future
    provider = flask.request.args.get('provider', PROVIDER)
    flask.session['oauth_provider'] = provider

    oauth_session = complinify(requests_oauthlib.OAuth2Session(
        client_id[provider],
        scope=scope[provider],
        redirect_uri=redirect_uri[provider]
    ))

    authorization_url, state = oauth_session.authorization_url(
        authorization_base_url[provider]
    )
    flask.session['oauth_state'] = state

    # return flask.redirect(authorization_url)
    return flask.jsonify({
        'message': 'Please login first',
        'location': authorization_url,
    })


@upload.route('/callback')
def callback():

    # to be set by request in future
    provider = flask.session.get('oauth_provider', PROVIDER)

    print(flask.session)

    oauth_session = complinify(requests_oauthlib.OAuth2Session(
        client_id[provider],
        state=flask.session.get('oauth_state', ''),
    ))

    token = oauth_session.fetch_token(
        token_url[provider],
        authorization_response=flask.request.url,
        client_secret=client_secret[provider],
    )

    flask.session['oauth_token'] = token

    return flask.redirect(
        flask.url_for('.info')
    )


@upload.route('/info')
def info():

    # to be set by request in future
    provider = flask.session.get('oauth_provider', PROVIDER)

    if 'oauth_token' in flask.session:
        oauth_session = complinify(requests_oauthlib.OAuth2Session(
            client_id[provider],
            token=flask.session['oauth_token'],
        ))
    else:
        return flask.redirect(
            flask.url_for('.init')
        )

    pprint.pprint(oauth_session)

    if provider == 'github':
        user_info = oauth_session.get(info_url[provider]).json()
        if provider == 'slack':
            username = user_info.get('profile', {}).get('email', '')
        else:
            username = ''
        username = user_info[username_key[provider]]
        team_info = oauth_session.get(team_info_url(username)[provider]).json()
        organization = team_info[0]['login']
        teams_info = oauth_session.get(f'https://api.github.com/repos/SUNCAT-Center/CatKit/collaborators').json()

        return flask.redirect(
            flask.url_for('.submit')
        )

        # return flask.jsonify({
        #'user': user_info,
        #'organization': team_info,
        #'org_id': organization,
        #'teams': teams_info,
        #'teams_url': f'https://api.github.com/orgs/{organization}/teams',

        #})
    elif provider == 'slack':
        user_info = oauth_session.get(info_url[provider]).json()
        team_info = oauth_session.get(team_info_url('')[provider]).json()
        flask.session['team_info'] = team_info
        flask.session['user_info'] = user_info
        return flask.redirect(
            flask.url_for('.submit')
        )


@upload.route('/submit')
def submit():
    if 'team_info' in flask.session:
        team_id = flask.session['team_info'].get('team', {}).get('id', '')

        if team_id and team_id == os.environ.get('SLACK_SUNCAT_TEAM_ID', ''):
            flask.session['LOGGED_IN'] = True
            return flask.redirect('https://www.catalysis-hub.org/upload?login=success')
        else:
            flask.session['LOGGED_IN'] = False
            return flask.redirect('https://www.catalysis-hub.org/upload?login=error')

    else:
        return flask.redirect(
            flask.url_for('.init')
        )


@upload.route('/logout', methods=['GET', 'POST'])
def logout():
    flask.session.clear()
    return flask.jsonify({
        'message': 'Logged out',
    })


@upload.route('/user_info', methods=['GET', 'POST'])
def user_info():
    provider = flask.request.args.get('provider', PROVIDER)
    authorization_url = authorization_base_url[provider]

    print(flask.session)
    if 'team_info' in flask.session:
        team_id = flask.session['team_info'].get('team', {}).get('id', '')
        if team_id and team_id == os.environ.get('SLACK_SUNCAT_TEAM_ID', ''):
            return flask.jsonify({
                'username': flask.session.get('user_info', {})
                .get('profile', {})
                .get('display_name', ''),
                'email': flask.session.get('user_info', {})
                .get('profile', {})
                .get('email', ''),
                'token': flask.session.get('oauth_token', {})
                .get('access_token', ''),
            })
        else:
            return flask.jsonify({
                'error': True,
                'message': 'Please login first',
                'location': authorization_url,
            })
    else:
        return flask.jsonify({
            'error': True,
            'message': 'Please login first',
            'location': authorization_url,
        })


@upload.route('/dataset/', methods=['GET', 'POST'])
def upload_dataset(request=None):
    request = flask.request if request is None else request
    filename = request.files['file'].filename
    suffix = os.path.splitext(filename)[1]
    if suffix == '.zip':
        message = ("You uploaded a zip file")
        suffix = 'ZIP'
    elif suffix in ['.tgz', '.tar.gz']:
        message = ("You uploaded a tar file.")
        suffix = 'TGZ'
    else:
        message = 'Could not detect filetype.'
        suffix = None

    with StringIO.BytesIO() as in_bfile:
        request.files['file'].save(in_bfile)

    return flask.jsonify({
        'message': message,
    })


@upload.route('/download_structure/', methods=['GET', 'POST'])
def download_structure(request=None):
    request = flask.request if request is None else request
    if type(request.args) is str:
        request.args = json.loads(request.args)

    input_str = str(request.args.get('input', ''))
    input_format = str(request.args.get('inputFormat', ''))
    output_format = str(request.args.get('outputFormat', inputFormat))

    with StringIO.StringIO() as infile:
        with StringIO.StringIO() as outfile:
            infile.write(input_str)
            infile.seek(0)
            atoms = ase.io.read(infile, format=input_format)
            ase.io.write(outfile, atom, format=output_format)

    response = flask.send_file(
        mem_file,
        attachment_filename=(output_format.upper()).format(**locals()),
    )
    return response


def userify_request(request, userhandle):
    ast = graphql.language.parser.parse(request)
    argument = graphql.language.ast.Argument(
        name=graphql.language.ast.Name(value='username'),
        value=graphql.language.ast.StringValue(value=userhandle))
    ast \
        .definitions[0] \
        .selection_set \
        .selections[0] \
        .arguments \
        .append(argument)


url = sqlalchemy.engine.url.URL('postgres',
                                username='upload_admin',
                                password=os.environ.get('UPLOAD_ADMIN_PASSWORD', ''),
                                host='catalysishub.c8gwuc8jwb7l.us-west-2.rds.amazonaws.com',
                                port=5432,
                                database='catalysishub', )

engine = sqlalchemy.create_engine(
    url,
    execution_options={
        'schema_translate_map': {
            'public': 'upload',
        }
    },
    convert_unicode=True)

db_session = sqlalchemy.orm.scoped_session(sqlalchemy.orm.sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
))

# Graphql view


def auth_required(fn, session):
    provider = flask.request.args.get('provider', PROVIDER)

    def wrapper(*args, **kwargs):
        pprint.pprint(session)
        if 'oauth_token' in flask.session:
            oauth_session = complinify(requests_oauthlib.OAuth2Session(
                client_id[provider],
                token=flask.session['oauth_token'],
            ))
            user_info = oauth_session.get(info_url[provider]).json()
            print("USER INFO")
            pprint.pprint(user_info)
            if provider == 'slack':
                username = user_info.get('profile', {}).get('email', '')
            else:
                username = ''
            team_info = oauth_session.get(
                team_info_url(username)[provider]).json()
            team_id = team_info.get('team', {}).get('id', '')
            if team_id != os.environ.get('SLACK_SUNCAT_TEAM_ID'):
                return flask.redirect(
                    flask.url_for('.init')
                )
        else:
            return flask.redirect(
                flask.url_for('.init')
            )

        return fn(*args, **kwargs)
    return wrapper


@upload.route('/release', methods=['POST', 'GET'])
def release():
    send_email(
        subject='Dataset Ready for Release',
        message='This is just a test.',
        recipient_emails=['mjhoffmann@gmail.com'],
    )
    return auth_required(flask.jsonify({
        'status': 'ok',
        'message': 'Submission received. Should be online in a few days. Thanks.'
    }), session=flask.session)


@upload.route('/graphql', methods=['POST', 'GET'])
def graphql_view():
    raw_view = flask_graphql.GraphQLView.as_view(
        'apps/upload/graphql',
        schema=api.schema,
        graphiql=True,
        context={
            'session': db_session,
        })

    # def view(*args, **kwargs):
    # print(inspect.getargspec(raw_view))
    # print(flask.request)
    # print(flask.request.data)
    # print(flask.request.args)
    # return raw_view(*args, **kwargs)
    # return (view)()

    return auth_required(raw_view, session=flask.session)()

    # print("ARGS")
    # print(flask.request.args)
    # print("REQUEST")
    # print(flask.request)
    # print("MIMETYPE")
    # print(flask.request.mimetype)
    #print("REQUEST DATA")
    # print(flask.request.data)
    #print("REQUEST VALUES")
    # print(flask.request.values)

    #query = json.loads(flask.request.data.decode('utf8')).get('query', '')
    # print("QUERY")
    # print(query)
    #print("TYPE QUERY")
    # print(type(query))

    # data = flask_graphql.GraphQLView.as_view(
    # schema=api.schema,
    ##context={ 'session': db_session, }
    # ).parse_body(flask.request)
    # print("DATA")
    # print(data)

    # execution_results, all_params = graphql_server.run_http_query(
    # schema=api.schema,
    # request_method=flask.request.method.lower(),
    # data={},
    #query_data={'query': query},
    # operationName='dummy',
    #)

    #print("EXECUTION RESULTS")
    # print(execution_results)

    # result, status_code = graphql_server.encode_execution_results(
    # execution_results,
    # is_batch=False,
    # format_error=(graphql_server.default_format_error),
    # encode=(graphql_server.json_encode),
    #)

    # print("ARGS")
    # print(flask.request.args)
    #print("EXECUTION RESULT")
    # print(execution_results)
    # print(dir(execution_results))
    # print(result)

    # return flask.Response(result)


# upload.add_url_rule(
    #'/graphql',
    # view_func=graphql_view(),
    #methods=['GET', 'POST'],
#)
