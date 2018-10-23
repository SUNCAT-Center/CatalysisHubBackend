import copy
import datetime
import functools
import inspect
import json
import logging
import os
import os.path
import pprint
import requests
import time
import zipfile


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
import flask_cors
import requests_oauthlib
import requests_oauthlib.compliance_fixes
import graphql_server

import ase.atoms
import ase.io
import ase.build

import models
import api

import sendgrid

from cathub.postgresql import CathubPostgreSQL

log = logging.getLogger(__name__)
log.setLevel(logging.DEBUG)

ADMIN_EMAILS = ['maxjh@stanford.edu', 'winther@stanford.edu']
FRONTEND_URL = 'https://www.catalysis-hub.org'

upload = flask.Blueprint('upload', __name__)

# Not secret, just needed to identify App.
client_id = {
    'github': '94895cb9f588ac74ab9d',
    'slack': '7745294259.330986790417',
    'google': '777817018775-mm6afmmpfcqtf8kso934elsslqqoludi.apps.googleusercontent.com',
}


scope = {
    'slack': ['users.profile:read', 'team:read'],
    'github': ['user:read'],
    'google': ["https://www.googleapis.com/auth/userinfo.email",
               "https://www.googleapis.com/auth/userinfo.profile"]
}

# Should be secret and only stored safely
client_secret = {
    'github': os.environ.get('GITHUB_CLIENT_SECRET', ''),
    'slack': os.environ.get('SLACK_CLIENT_SECRET', ''),
    'google': os.environ.get('GOOGLE_OAUTH_SECRET', ''),
}

for key, value in client_secret.items():
    if not value:
        print(f'Warning: client secret for {key} not set')


authorization_base_url = {
    'github': 'https://github.com/login/oauth/authorize',
    'slack': 'https://slack.com/oauth/authorize',
    'google': 'https://accounts.google.com/o/oauth2/v2/auth',
}

token_url = {
    'github': 'https://github.com/login/oauth/access_token',
    'slack': 'https://slack.com/api/oauth.access',
    'google': 'https://www.googleapis.com/oauth2/v4/token',
}

info_url = {
    'github': 'https://api.github.com/user',
    'slack': 'https://slack.com/api/users.profile.get',
    'google': 'https://www.googleapis.com/oauth2/v1/userinfo',
}

SG = sendgrid.SendGridAPIClient(apikey=os.environ.get('SENDGRID_API_KEY', '').strip())

def get_corresponding_email(pubId):
    query = {'query': """{{
        reactions(pubId:"{pubId}", first:1) {{
          edges {{
            node {{
             username
            }}
          }}
        }}}}
    """.format(**locals()).replace('\n', '')}
    response = requests.get(GRAPHQL_ROOT, query).json()
    return response['data']['reactions']['edges'][0]['node']['username']


def redirect_uri(url_root):
    res =  f'{url_root}apps/upload/callback'
    log.debug("REDIRECT URI")
    log.debug(res)
    return res


def send_email(
        subject="Hello from Catalysis-Hub.Org",
        message="This is a test message. Sorry, for the spam.",
        recipient_emails=[]
):

    recipient_emails.insert(0, 'no-reply@catalysis-hub.org')
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
    response = SG.client.mail.send.post(request_body=data)
    log.debug(response.status_code)


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


@upload.route('/', methods=['GET', 'POST', 'OPTIONS'])
@flask_cors.cross_origin(supports_credentials=True,origin='*',headers=['Content-Type','Authorization'])
def init():
    log.debug("@@@ UPLOAD ROOT ROUTE")
    log.debug("FLASK HEADERS")
    log.debug(flask.request.headers)
    log.debug("FLASK SESSION")
    log.debug(flask.session)
    log.debug("FLASK REQUEST")
    log.debug(flask.request.url_root)
    # to be set by request in future
    provider = flask.request.args.get('provider', PROVIDER)
    flask.session['oauth_provider'] = provider


    oauth_session = complinify(requests_oauthlib.OAuth2Session(
        client_id[provider],
        scope=scope[provider],
        redirect_uri=redirect_uri(flask.request.url_root)
    ))

    authorization_url, state = oauth_session.authorization_url(
        authorization_base_url[provider]
    )
    flask.session['oauth_state'] = state

    log.debug("UPLOAD ROOT SESSION")
    log.debug(flask.session)

    return flask.jsonify({
        'message': 'Please login first',
        'location': authorization_url,
    })


@upload.route('/callback')
@flask_cors.cross_origin(supports_credentials=True,origin='*',headers=['Content-Type','Authorization'])
def callback():
    log.debug("@@@ CALLBACK ROUTE")

    # to be set by request in future
    provider = flask.session.get('oauth_provider', PROVIDER)

    log.debug(flask.session)

    log.debug("PROVIDER")
    log.debug(provider)

    log.debug("TOKENURL")
    log.debug(token_url[provider])

    log.debug("FLASK REQUEST URL")
    log.debug(flask.request.url)

    log.debug("CLIENT SECRET")
    log.debug(client_secret[provider])

    log.debug("SESSION")
    log.debug(flask.session)

    oauth_session = complinify(requests_oauthlib.OAuth2Session(
        client_id=client_id[provider],
        redirect_uri=redirect_uri(flask.request.url_root),
        state=flask.session.get('oauth_state', ''),
    ), provider=provider)


    log.debug("OAUTH SESSION")
    log.debug(oauth_session)

    log.debug('_client ' + str(oauth_session._client))
    log.debug('token ' + str(oauth_session.token))
    log.debug('scope ' + str(oauth_session.scope))
    log.debug('redirect_uri ' + str(oauth_session.redirect_uri))
    log.debug('state ' + str(oauth_session.state))
    log.debug('_state ' + str(oauth_session._state))
    log.debug('auto_refresh_url ' + str(oauth_session.auto_refresh_url))
    log.debug('auto_refresh_kwargs' + str(oauth_session.auto_refresh_kwargs))
    log.debug('token_updater ' + str(oauth_session.token_updater))

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
@flask_cors.cross_origin(supports_credentials=True,origin='*',headers=['Content-Type','Authorization'])
def info():
    log.debug("@@@ INFO ROUTE")
    log.debug("SESSION")
    log.debug(flask.session)

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

    elif provider == 'slack':
        user_info = oauth_session.get(info_url[provider]).json()
        team_info = oauth_session.get(team_info_url('')[provider]).json()
        flask.session['team_info'] = team_info
        flask.session['user_info'] = user_info
        return flask.redirect(
            flask.url_for('.submit')
        )

    elif provider == 'google':
        user_info = oauth_session.get(info_url[provider]).json()
        flask.session['user_info'] = user_info
        return flask.redirect(
            flask.url_for('.submit')
        )

@upload.route('/submit', methods=['GET', 'POST'])
@flask_cors.cross_origin(supports_credentials=True,origin='*',headers=['Content-Type','Authorization'])
def submit():
    return auth_required(
        flask.redirect(FRONTEND_URL + '/upload?login=success'),
        session=flask.session
            )

@upload.route('/logout', methods=['GET', 'POST'])
@flask_cors.cross_origin(supports_credentials=True,origin='*',headers=['Content-Type','Authorization'])
def logout():
    log.debug("@@@ LOGOUT ROUTE")
    flask.session.clear()
    return flask.jsonify({
        'message': 'Logged out',
    })


@upload.route('/user_info', methods=['GET', 'POST'])
@flask_cors.cross_origin(supports_credentials=True,origin='*',headers=['Content-Type','Authorization'])
def user_info():
    log.debug("@@@ USER_INFO ROUTE")
    provider = flask.request.args.get('provider', PROVIDER)
    authorization_url = authorization_base_url[provider]

    log.debug("#### SESSION BEFORE AUTH")
    log.debug(flask.session)
    return auth_required(flask.jsonify({
                'username': flask.session.get('user_info', {})
                .get('profile', {})
                .get('display_name', ''),
                'email': flask.session.get('user_info', {})
                .get('profile', {})
                .get('email', ''),
                'token': flask.session.get('oauth_token', {})
                .get('access_token', ''),
                'picture': flask.session.get('user_info', {})
                .get('profile')
                .get('picture', '')
            }), session=flask.session)



@upload.route('/dataset/', methods=['GET', 'POST'])
@flask_cors.cross_origin(supports_credentials=True,origin='*',headers=['Content-Type','Authorization'])
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
@flask_cors.cross_origin(supports_credentials=True,origin='*',headers=['Content-Type','Authorization'])
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
    provider = session.get('oauth_provider', PROVIDER)

    def wrapper(*args, **kwargs):
        log.debug("-> AUTH_REQUIRED")
        log.debug(session)
        if 'oauth_token' in flask.session:
            oauth_session = complinify(requests_oauthlib.OAuth2Session(
                client_id[provider],
                token=flask.session['oauth_token'],
            ))
            user_info = oauth_session.get(info_url[provider]).json()
            log.debug("USER INFO")
            log.debug(user_info)
            log.debug("PROVIDER")
            log.debug(provider)
            session['user_info'] = user_info
            if provider == 'slack':
                username = user_info.get('profile', {}).get('email', '')
                team_info = oauth_session.get(
                    team_info_url(username)[provider]).json()
                team_id = team_info.get('team', {}).get('id', '')
                if team_id != os.environ.get('SLACK_SUNCAT_TEAM_ID'):
                    return flask.redirect(
                        flask.url_for('.init')
                    )

                session.setdefault('user_info', {}) \
                       .setdefault('profile', {}) \
                       .setdefault('picture', user_info.get('profile', {}).get('image_72'))



            elif provider == 'google':
                session.pop('user_info')
                session.setdefault('user_info', {}) \
                       .setdefault('profile', user_info)
            else:
                return flask.redirect(
                    flask.url_for('.init')
                )
        else:
            return flask.redirect(
                flask.url_for('.init')
            )

        return fn(*args, **kwargs)
    return wrapper


def f():
    return True


@upload.route('/delete', methods=['POST', 'GET'])
def delete():
    if auth_required(f, session=flask.session):
        params = flask.request.get_json()
        endorser = params.get('userInfo', {}).get('username', '')
        endorser_email = params.get('userInfo',{}).get('email', '')
        pub_id = params.get('dataset', {}).get('pubId', '')

        cathub_db = CathubPostgreSQL(user='upload_admin',
                                     password=os.environ.get('UPLOAD_ADMIN_PASSWORD'))
        userhandle = cathub_db.get_pub_id_owner(pub_id)

        if not userhandle == endorser_email:
            return flask.jsonify({
                 'status': 'Failed',
                 'message': "You don't have permission to delete this dataset"
             })

        cathub_db.delete_publication(pub_id)

        return flask.jsonify({
                 'status': 'ok',
                 'message': "The dataset '{}' was succesfully deleted".format(pub_id)
             })


@upload.route('/release', methods=['POST', 'GET'])
def release():
    if auth_required(f, session=flask.session):
        log.debug("FLASK VALUES")
        log.debug(flask.request.get_json())
        params = flask.request.get_json()
        endorser = params.get('userInfo', {}).get('username', '')
        endorser_email = params.get('userInfo',{}).get('email', '')
        pub_id = params.get('dataset', {}).get('pubId', '')
        title = params.get('dataset', {}).get('title', '')
        corresponding_email = params.get('corresponding_email', '')

        send_email(
            subject='[Catalysis-Hub.Org] Dataset {title} Was Released'.format(**locals()),
            message="""
Greeting from Catalysis-Hub.Org!

{endorser} wants to release the dataset {title} ({pub_id}) to the public.

Thanks {endorser} for your contribution!

It should appear soon under https://www.catalysis-hub.org/publications/{pub_id}.
    """.format(**locals()),
            recipient_emails=list(set([endorser_email, corresponding_email] + ADMIN_EMAILS)),
        )

        return flask.jsonify({
            'status': 'ok',
            'message': 'Submission received. Should be online in a few days. Thanks.'
        })


@upload.route('/endorse', methods=['POST', 'GET'])
def endorse():
    if auth_required(f, session=flask.session):
        log.debug("FLASK VALUES")
        log.debug(flask.request.get_json())
        params = flask.request.get_json()
        endorser = params.get('userInfo', {}).get('username', '')
        endorser_email = params.get('userInfo',{}).get('email', '')
        pub_id = params.get('dataset', {}).get('pubId', '')
        title = params.get('dataset', {}).get('title', '')
        corresponding_email = params.get('corresponding_email', '')

        send_email(
            subject='[Catalysis-Hub.Org] Dataset {title} Was Endorsed'.format(**locals()),
            message="""
Greetings from Catalysis-Hub.Org!

{endorser} has shown interest in your dataset "{title}".

Are you ready to release it? Please go to https://www.catalysis-hub.org/upload for the next steps.
    """.format(**locals()),
            recipient_emails=list(set([endorser_email, corresponding_email] + ADMIN_EMAILS)),
        )

        return flask.jsonify({
            'status': 'ok',
            'message': 'Thanks for the endorsement, we will let the author know.'
        })



@upload.route('/graphql', methods=['POST', 'GET'])
def graphql_view():
    raw_view = flask_graphql.GraphQLView.as_view(
        'apps/upload/graphql',
        schema=api.schema,
        graphiql=True,
        context={
            'session': db_session,
        })

    return auth_required(raw_view, session=flask.session)()
