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

ROOT = 'https://38f39877.ngrok.io'
ROOT = 'http://catappdatabase2.herokuapp.com/graphql'
ROOT = 'http://127.0.0.1:5000/graphql'

def reactant_query(reactant="O"):
    print("REACTANT QUERY {reactant}".format(**locals()))
    query = {'query': """{{
      reactions(reactants: "{reactant}") {{
        edges {{
          node {{
            reactionEnergy
            reactionSystems {{
              name
              systems {{
                uniqueId
                Formula
                Facet
              }}
            }}
          }}
        }}
        totalCount
      }}
    }}""".format(**locals())}
    print(ROOT)
    print(query['query'].replace('\n', ''))
    return  requests.get(ROOT, query).json()



@activityMaps.route('/systems/', methods=['GET', 'POST'])
def systems(request=None):
    request = flask.request if request is None else request
    if type(request.args) is str:
        request.args = json.loads(request.args)

    # unpack arguments
    activityMap = str(request.args.get('activityMap', 'OER'))
    CACHE_FILE = 'reaction_systems_{activityMap}.json'.format(**locals())

    if activityMap == 'OER':
        reactants = ['O', 'OH', 'OOH']
        print(reactants)
        if os.path.exists(CACHE_FILE):
            with open(CACHE_FILE) as infile:
                raw_systems = json.loads(infile.read())
        else:
            raw_systems = {}
            for reactant in reactants:
                print(reactant)
                raw_systems[reactant] = reactant_query(reactant)
            with open(CACHE_FILE, 'w') as outfile:
                #outfile.write(json.dumps(raw_systems, sort_keys=True, indent=1, separators=(',', ': ')))
                outfile.write(json.dumps(raw_systems, ))

        complete_reactions = 0
        incomplete_reactions = 0

        #return flask.jsonify({
            #'reactants': reactants,
            #'raw_systems': raw_systems,
            #})

        systems = {}
        for reactant in raw_systems:
            print(reactant)
            for edge in raw_systems[reactant]['data']['reactions']['edges']:
                pprint.pprint(edge)
                print(list(map(lambda x: x['name'], edge['node']['reactionSystems'])))
                star_list = list(filter(lambda x: x['name'] == 'star', edge['node']['reactionSystems']))
                if len(star_list) == 0:
                    continue
                star = star_list[0]

                #print(star)
                uniqueId = star['systems']['uniqueId']
                #systems.setdefault(reactant, {}).setdefault(uniqueId, []).append(star)
                systems.setdefault(uniqueId, {})[reactant] =  {
                    'systems': edge['node']['reactionSystems'],
                    'energy': edge['node']['reactionEnergy']
                        }

        short_systems = []
        for uid in systems:
            print(len(systems[uid].keys()))
            if len(systems[uid].keys())  == 3:
                complete_reactions += 1
                #print("\n\nUID {uid}\n====================================\n".format(**locals()))
                #pprint.pprint(systems[uid])
                energies = {}
                for reactant in systems[uid]:
                    star = list(filter(lambda x: x['name'] == 'star', systems[uid][reactant]['systems']))[0]
                    #pprint.pprint(star)
                    facet = star['systems']['Facet']
                    formula = star['systems']['Formula']
                    energy = systems[uid][reactant]['energy']
                    energies[reactant] = energy
                    #print('{facet:20s}{formula:20s}{reactant:20s}{energy:+.3f}'.format(**locals()))
                    #print(, , reactant, )

                dE_OH = energies['OH']
                dE_O__dE_OH = energies['O'] - energies['OH']

                print('{uid}\t{formula:20s}{facet:20s}dE(OH) = {dE_OH:.3f}\tdE(O) - dE(OH) = {dE_O__dE_OH:.3f}'.format(**locals()))
                system_name = '{formula:20s}{facet:20s}'.format(**locals())
                short_systems.append({
                    'uid': uid,
                    'formula': formula,
                    'facet': facet,
                    'dE_OH': dE_OH,
                    'dE_O__dE_OH ':dE_O__dE_OH,
                    })
            else:
                incomplete_reactions += 1

    return flask.jsonify({
        'systems': short_systems,
        })
