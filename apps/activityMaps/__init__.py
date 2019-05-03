# -*- coding: utf-8
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
except ImportError:
    import StringIO

import numpy as np

import requests
import flask

import ase.atoms
import ase.io
import ase.build

activityMaps = flask.Blueprint('activityMaps', __name__)

GRAPHQL_ROOT = 'http://api.catalysis-hub.org/graphql'
ROOT = 'http://api.catalysis-hub.org/'


class ReactionModel(object):

    def __init__(self, xlabel=None, ylabel=None, zlabel=None, reference=''):
        self.xlabel = xlabel
        self.ylabel = ylabel
        self.zlabel = zlabel
        self.reference = reference

    def get_raw_systems(self, filters):
        pass

    def get_xyz(self, systems):
        pass


def graphql_query(products='products: "O"',
                  reactants='', facet='', pub_id=None, limit=5000):
    publication = ''
    if pub_id is not None:
        publication = ' pubId: "{}"'.format(pub_id)

    query = {'query': """{{
      reactions(first: {limit}, {reactants}{products}{facet}{publication}) {{
        edges {{
          node {{
            pubId
            reactionEnergy
            sites
            facet
            chemicalComposition
            reactionSystems {{
                name
                aseId
            }}
          }}
        }}
      }}
    }}""".format(**locals()).replace('\n', '')}

    response = requests.get(GRAPHQL_ROOT, query).json()

    return response


@activityMaps.route('/systems/', methods=['GET', 'POST'])
def systems(request=None):
    """
    GET: Get systems for given reactions

    Args:
        activityMap(str): request Map like OER, NRR, HER.
                          Defaults to CO_Hydrogenation_111.

    Returns:
        dict: The corresponding systems in the database.
            * reference(str): Reference for activity map.
            * systems(list): Corresponding systems.

    Examples:
        .. code-block:: bash

            curl {ROOT}/apps/activityMaps/systems/?activityMap=OER
            curl {ROOT}/apps/activityMaps/systems/?activityMap=CO_Hydrogenation_111

        .. code-block:: json

            {
          "reference": "[1] Friebel, Daniel, Mary W. Louie, Michal Bajdich, Kai E. Sanwald, Yun Cai, Anna M. Wise, Mu-Jeng Cheng et al. \"Identification of highly active Fe sites in (Ni, Fe) OOH for electrocatalytic water splitting.\" Journal of the American Chemical Society 137, no. 3 (2015): 1305-1313. DOI: 10.1021/ja511559d [2] Man, Isabela C., Hai\u2010Yan Su, Federico Calle\u2010Vallejo, Heine A. Hansen, Jos\u00e9 I. Mart\u00ednez, Nilay G. Inoglu, John Kitchin, Thomas F. Jaramillo, Jens K. N\u00f8rskov, and Jan Rossmeisl. \"Universality in oxygen evolution electrocatalysis on oxide surfaces.\" ChemCatChem 3, no. 7 (2011): 1159-1165. DOI: 10.1002/cctc.201000397",
          "systems": [
            {
              "facet": "3ML",
              "formula": "Ir16Sr4O51",
              "uid": "5b0b436e4d3d07c3fb7a4cee6d5975f1",
              "x": 1.5028540934200003,
              "y": 1.3901226701799998,
              "z": -0.3208143060400004
            },
            {
              "facet": "100",
              "formula": "Ir24O53",
              "uid": "b33747e9868b9514639752f1b58e2f03",
              "x": 1.4204331210799999,
              "y": 0.44616836241,
              "z": -0.4164322559
            }, ] }

    """

    request = flask.request if request is None else request
    if isinstance(request.args, str):
        request.args = json.loads(request.args)

    # unpack arguments
    activityMap = str(request.args.get('activityMap', 'OER'))
    pub_id = request.args.get('pubId', None)
    short_systems = []
    raw_systems = {}
    labels = {}
    if activityMap == 'OER':
        def overpotential(doh, do, dooh=None):

            def ooh_oh_scaling(doh):
                # like ambars
                # dooh=0.5*doh  + 3.0		 #O
                # normal one
                dooh = doh + 3.2
                return dooh

            if dooh is None:
                dooh = ooh_oh_scaling(doh)
            dg14 = [doh, do - doh, dooh - do, -dooh + 4.92]
            m = max(dg14)
            return m - 1.23

        reactants = ['OOH', 'OH', 'O', ]

        raw_systems = {}
        raw_systems['OH'] = {'data': {'reactions': {'edges': []}}}
        raw_systems['O'] = {'data': {'reactions': {'edges': []}}}

        reactant = 'OOH'
        raw_systems[reactant] = graphql_query(
            products='products: "' + reactant + '", ', pub_id=pub_id)

        OOH_pub_ids = []
        for reactant in raw_systems:
            for edge in raw_systems[reactant]['data']['reactions']['edges']:
                pub_id_sub = edge['node']['pubId']
                if not pub_id in OOH_pub_ids:
                    OOH_pub_ids = [pub_id_sub]

        for reactant in ['OH', 'O']:
            for pub_id_sub in OOH_pub_ids:
                raw_systems[reactant]['data']['reactions']['edges'] += graphql_query(
                    products='products: "' + reactant + '", ',
                    pub_id=pub_id_sub)['data']['reactions']['edges']

        systems = {}
        for reactant in raw_systems:
            for edge in raw_systems[reactant]['data']['reactions']['edges']:
                star_list = list(filter(lambda x: x['name'] == 'star', edge[
                                 'node']['reactionSystems']))
                if len(star_list) == 0:
                    continue
                star = star_list[0]

                uniqueId = star['aseId']
                systems.setdefault(uniqueId, {})['facet'] = edge[
                    'node']['facet']
                systems.setdefault(uniqueId, {})['chemicalComposition'] = edge[
                    'node']['chemicalComposition']
                systems.setdefault(
                    uniqueId,
                    {}).setdefault(
                    'reactants',
                    {})[reactant] = {
                    'systems': edge['node']['reactionSystems'],
                    'energy': edge['node']['reactionEnergy'],
                }

        for uid in systems:
            if len(systems[uid]['reactants'].keys()) == len(reactants):
                energies = {}
                formula = systems[uid]['chemicalComposition']
                facet = systems[uid]['facet']

                for reactant in systems[uid]['reactants']:
                    star = list(filter(lambda x: x['name'] == 'star', systems[
                                uid]['reactants'][reactant]['systems']))[0]
                    energy = systems[uid]['reactants'][reactant]['energy']
                    energies[reactant] = energy

                error_correction = +1  # to be fixed in API
                dE_OH = error_correction * energies['OH']
                dE_O = error_correction * energies['O']
                dE_OOH = error_correction * energies['OOH']

                # cf. https://pubs.acs.org/doi/pdfplus/10.1021/jacs.7b02622
                dG_OH = dE_OH + 0.30225
                dG_O = dE_O + (-0.0145)
                dG_OOH = dE_OOH + 0.34475

                dG_O__dG_OH = dG_O - dG_OH

                system_name = '{formula:20s}{facet:20s}'.format(**locals())
                short_systems.append({
                    'uid': uid,
                    'formula': formula,
                    'facet': facet,
                    'x': dG_O__dG_OH,
                    'y': dG_OH,
                    'z': overpotential(dG_OH, dG_O, dG_OOH),
                })
        labels.update({
            'xlabel': 'ΔG(O) - ΔG(OH) [eV]',
            'ylabel': 'ΔG(OH) [eV]',
            'zlabel': 'Overpotential [eV]',
            'reference': ('[1] Friebel, Daniel, Mary W. Louie,'
                          ' Michal Bajdich, Kai E. Sanwald, Yun Cai,'
                          ' Anna M. Wise, Mu-Jeng Cheng et al.'
                          ' "Identification of highly active Fe sites'
                          ' in (Ni, Fe) OOH for electrocatalytic water'
                          ' splitting." Journal of the American Chemical'
                          ' Society 137, no. 3 (2015): 1305-1313.'
                          ' DOI: 10.1021/ja511559d [2] Man, Isabela C.,'
                          ' Hai‐Yan Su, Federico Calle‐Vallejo,'
                          ' Heine A. Hansen, José I. Martínez,'
                          ' Nilay G. Inoglu, John Kitchin,'
                          ' Thomas F. Jaramillo, Jens K. Nørskov,'
                          ' and Jan Rossmeisl. "Universality in'
                          ' oxygen evolution electrocatalysis on'
                          ' oxide surfaces." ChemCatChem 3, no. 7 (2011):'
                          ' 1159-1165. DOI: 10.1002/cctc.201000397')
        })

    elif activityMap == 'NRR':
        def limiting_potential(dG_NNH, dG_NH2__dG_NH):
            return max(dG_NNH, dG_NH2__dG_NH)

        raw_systems = {}
        raw_systems['NNH'] = graphql_query(
            reactants='reactants: "star+H2gas+N2gas",',
            products='products: "NNHstar" ,',
            facet='facet: "' + '~111' + '", ',
            pub_id=pub_id
        )

        NNH_pub_ids = []
        for reactant in raw_systems:
            for edge in raw_systems[reactant]['data']['reactions']['edges']:
                pub_id_sub = edge['node']['pubId']
                if not pub_id in NNH_pub_ids:
                    NNH_pub_ids = [pub_id_sub]

        raw_systems['NH2'] = {'data': {'reactions': {'edges': []}}}
        raw_systems['NH'] = {'data': {'reactions': {'edges': []}}}

        for pub_id_sub in NNH_pub_ids:
            raw_systems['NH2']['data']['reactions']['edges'] += graphql_query(
                reactants='reactants: "star+H2gas+N2gas",',
                products=' products: "NH2star", ',
                facet='facet: "' + '~111' + '", ',
                pub_id=pub_id_sub
            )['data']['reactions']['edges']

            raw_systems['NH']['data']['reactions']['edges'] += graphql_query(
                reactants='reactants: "star+H2gas+N2gas",',
                products='products: "NHstar", ',
                facet='facet: "' + '~111' + '", ',
                pub_id=pub_id_sub
            )['data']['reactions']['edges']

        systems = {}
        for reactant in raw_systems:
            for raw_system in raw_systems[reactant]['data']['reactions']['edges']:
                for geometry in raw_system['node'].get('reactionSystems', {}):
                    if geometry['name'] == 'star':
                        site = list(json.loads(
                            raw_system['node']['sites']
                        ).values())[0]
                        formula = raw_system['node']['chemicalComposition']

                        # skip unstable sites by now
                        # to be removed.
                        if (reactant, formula, site) in [
                                ('NNH', 'Au16', 'ontop'),
                                ('NNH', 'Au16', 'fcc'),
                                ('NNH', 'Au16', 'hollow'),
                                ('NNH', 'Pd16', 'ontop'),
                                ('NNH', 'Pt16', 'ontop'),
                                ('NNH', 'Rh16', 'ontop'),
                        ]:
                            continue

                        system = systems.setdefault(geometry['aseId'], {})
                        energy = system.get('E', {})
                        energy.setdefault(reactant, {}) \
                              .setdefault(site, raw_system['node']['reactionEnergy'])
                        system.update({
                            'formula': raw_system['node']['chemicalComposition'],
                            'facet': raw_system['node']['facet'],
                            'uid': geometry['aseId'],
                            'E': energy,
                        })

        for uid in systems:
            system = systems[uid]
            dE_NNH = sorted(list(system['E']['NNH'].values()))[0]
            dE_NH2 = sorted(list(system['E']['NH2'].values()))[0]
            dE_NH = sorted(list(system['E']['NH'].values()))[0]

            #  free energy corrections from Aayush Singh
            dG_NNH = dE_NNH + 0.763
            # 0.763 eV, free energy correction
            dG_NH2__dG_NH = dE_NH2 - dE_NH + 0.330
            # 0.330 eV, free energy correction

            U_L = limiting_potential(dG_NNH, dG_NH2__dG_NH)

            # system.pop('E')
            system.update({
                'x': dG_NNH,
                'y': dG_NH2__dG_NH,
                'z': U_L,
            })

        short_systems = [
            system for system in
            systems.values()
        ]

        labels.update({
            'xlabel': 'ΔG(NNH) [eV]',
            'ylabel': 'ΔG(NH2) - ΔG(NH) [eV]',
            'zlabel': 'U(L) [V s. RHE]',
            'reference': ('Montoya, Joseph H., Charlie Tsai,'
                          ' Aleksandra Vojvodic, and Jens K. Nørskov.'
                          ' "The challenge of electrochemical ammonia'
                          ' synthesis: A new perspective on the role of'
                          ' nitrogen scaling relations." ChemSusChem 8,'
                          ' no. 13 (2015): 2180-2186.'
                          ' DOI: 10.1002/cssc.201500322.'
                          ' Free energy corrections correspond to'
                          ' Ru(111) surface and N2/H2 gas phase at 300K'
                          ' and standard pressure.'),
        })

    elif activityMap == 'ORR':
        labels.update({
            'xlabel': 'ΔG(OH) [eV]',
            'ylabel': 'ΔG(OOH) [eV]',
            'zlabel': 'Overpotential [eV]',
            'reference': ('Kulkarni, Ambarish, Samira Siahrostami,'
                          ' Anjli Patel, and Jens K. Nørskov. "Understanding'
                          ' Catalytic Activity Trends in the Oxygen Reduction'
                          ' Reaction." Chemical reviews (2018).'
                          ' DOI: 10.1021/acs.chemrev.7b00488'),
        })

    elif activityMap == 'CO_Hydrogenation_111':
        raw_systems = {}
        raw_systems['COstar'] = list(map(
            lambda x: x['node'],
            graphql_query(
                products='products: "' + 'COstar' + '", ',
                reactants='reactants: "' + 'COgas' + '", ',
                facet='facet: "' + '111' + '", ',
            )['data']['reactions']['edges']
        ))

        raw_systems['OHstar'] = list(map(
            lambda x: x['node'],
            graphql_query(
                products='products: "' + 'H2gas+OHstar' + '", ',
                reactants='reactants: "' + 'H2Ogas' + '", ',
                facet='facet: "' + '111' + '", ',
            )['data']['reactions']['edges']
        ))

        systems = {}
        for reactant in raw_systems:
            for raw_system in raw_systems[reactant]:
                for geometry in raw_system.get('reactionSystems', {}):
                    if geometry['name'] == 'star':
                        system = systems.setdefault(geometry['aseId'], {})
                        system.update({
                            'formula': raw_system['chemicalComposition'],
                            'facet': raw_system['facet'],
                            'uid': geometry['aseId'],
                        })
                        if reactant == 'COstar':
                            system.update({
                                'x': raw_system['reactionEnergy'],
                                'z': 0.0,
                            })
                        elif reactant == 'OHstar':
                            system.update({
                                'y': raw_system['reactionEnergy'],
                                'z': 0.0,
                            })

        short_systems = [
            system for system in
            systems.values()
            if system.get('x', None) and system.get('y', None)
        ]

        labels.update({
            'xlabel': 'ΔE(CO) [eV]',
            'ylabel': 'ΔE(OH) [eV]',
            'zlabel': 'TOF [1/s]',
            'reference': ('Schumann, Julia, Andrew J. Medford,'
                          ' Jong Suk Yoo, Zhi-Jian Zhao, Pallavi Bothra,'
                          ' Ang Cao, Felix Studt, Frank Abild-Pedersen,'
                          ' and Jens K. Nørskov. "Selectivity of synthesis'
                          ' gas conversion to C2+ oxygenates on fcc (111)'
                          ' transition metal surfaces." ACS Catalysis (2018).'
                          ' DOI: 10.1021/acscatal.8b00201.'),
        })

    elif activityMap == 'CO2RR':
        labels.update({
            'xlabel': 'ΔE(CO*) [eV]',
            'ylabel': 'ΔE(H-CO) [eV]',
            'zlabel': 'log(TOF) [1/s]',
            'reference': ('Liu, Xinyan, Jianping Xiao, Hongjie Peng,'
                          ' Xin Hong, Karen Chan, and Jens K. Nørskov.'
                          ' "Understanding trends in electrochemical'
                          ' carbon dioxide reduction rates."'
                          ' Nature Communications 8 (2017): 15438.'),
        })

    # sort for top systems list

    short_systems = sorted(
        short_systems,
        key=lambda _x: - _x.get('z', 0.0)
    )

    return flask.jsonify({
        'systems': short_systems,
        'xlabel': labels.get('xlabel', ''),
        'ylabel': labels.get('ylabel', ''),
        'zlabel': labels.get('zlabel', ''),
        'reference': labels.get('reference', ''),
    })
