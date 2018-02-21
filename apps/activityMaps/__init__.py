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

import requests
import flask

import ase.atoms
import ase.io
import ase.build

activityMaps = flask.Blueprint('activityMaps', __name__)

ROOT = 'http://127.0.0.1:5000/graphql'
ROOT = 'http://2f4bb6d4.ngrok.io/graphql/'
ROOT = 'http://catappdatabase2.herokuapp.com/graphql'


def reactant_query(reactant="O", limit=50):
    query = {'query': """{{
      reactions( reactants: "{reactant}") {{
        edges {{
          node {{
            reactionEnergy
              systems {{
                uniqueId
                Formula
                Facet
              }}
          }}
        }}
        totalCount
      }}
    }}""".replace('\n', '').format(**locals())}
    print(query)

    return requests.get(ROOT, query).json()



@activityMaps.route('/systems/', methods=['GET', 'POST'])
def systems(request=None):
    request = flask.request if request is None else request
    if type(request.args) is str:
        request.args = json.loads(request.args)

    # unpack arguments
    activityMap = str(request.args.get('activityMap', 'OER'))
    CACHE_FILE = 'reaction_systems_{activityMap}.json'.format(**locals())

    if activityMap == 'OER':
        reactants = ['OOH', 'OH', 'O', ]
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE) as infile:
                raw_systems = json.loads(infile.read())
        else:
            raw_systems = {}
            for reactant in reactants:
                raw_systems[reactant] = reactant_query(reactant)
            with open(CACHE_FILE, 'w') as outfile:
                outfile.write(json.dumps(raw_systems, ))

        systems = {}
        for reactant in raw_systems:
            for edge in raw_systems[reactant]['data']['reactions']['edges']:
                star_list = list(filter(lambda x: x['name'] == 'star', edge['node']['reactionSystems']))
                if len(star_list) == 0:
                    continue
                star = star_list[0]

                uniqueId = star['systems']['uniqueId']
                #systems.setdefault(reactant, {}).setdefault(uniqueId, []).append(star)
                systems.setdefault(uniqueId, {})[reactant] =  {
                    'systems': edge['node']['reactionSystems'],
                    'energy': edge['node']['reactionEnergy']
                        }

        short_systems = []
        for uid in systems:
            if len(systems[uid].keys())  == len(reactants):
                energies = {}
                for reactant in systems[uid]:
                    star = list(filter(lambda x: x['name'] == 'star', systems[uid][reactant]['systems']))[0]
                    facet = star['systems']['Facet']
                    formula = star['systems']['Formula']
                    energy = systems[uid][reactant]['energy']
                    energies[reactant] = energy

                error_correction = -1 # to be fixed in API
                dE_OH = error_correction * energies['OH']
                dE_O =  error_correction * energies['O']
                dE_OOH = error_correction * energies['OOH']

                # cf. https://pubs.acs.org/doi/pdfplus/10.1021/jacs.7b02622
                dG_OH = dE_OH + 0.30225 
                dG_O = dE_O + ( -0.0145  )
                dG_OOH =  dE_OOH + 0.34475

                dG_O__dG_OH = dG_O - dG_OH
                

                system_name = '{formula:20s}{facet:20s}'.format(**locals())
                short_systems.append({
                    'uid': uid,
                    'formula': formula,
                    'facet': facet,
                    'y': dG_OH,
                    'x': dG_O__dG_OH,
                    })

    return flask.jsonify({
        'systems': short_systems,
        })
