"""Base feature generation."""
from __future__ import absolute_import
from __future__ import division

import numpy as np
import json

from ase.data import ground_state_magnetic_moments, atomic_numbers
from mendeleev import element


def return_features(inp):
    """Return feature space."""
    # Open previously generated features.
    with open('raw_data/feature_store.json', 'r') as featurefile:
        store_dict = json.load(featurefile)

    # Pull out all relevant features for supplied system.
    afinger = np.asarray(store_dict['adsdict'][inp['a']], np.float64)
    facetfinger = np.asarray(store_dict['facetdict'][inp['facet']], np.float64)
    m1finger = np.asarray(store_dict['elemdict'][inp['m1']], np.float64)
    m2finger = np.asarray(store_dict['elemdict'][inp['m2']], np.float64)
    msum = list(np.nansum([m1finger + m2finger], axis=0, dtype=float))
    concfinger = np.asarray([inp['conc']], np.float64)
    sitefinger = np.asarray(store_dict['sitedict'][inp['site']], np.float64)

    return np.concatenate((afinger, m1finger, m2finger, concfinger,
                           facetfinger, sitefinger, msum))


def _n_outer(econf):
    """Return a list of the number of electrons in each shell.

    Parameters
    ----------
    econf : str
        electron configuration.
    """
    n_tot, ns, np, nd, nf = 0, 0, 0, 0, 0
    for shell in econf.split(' ')[1:]:
        n_shell = 0
        if shell[-1].isalpha():
            n_shell = 1
        elif len(shell) == 3:
            n_shell = int(shell[-1])
        elif len(shell) == 4:
            n_shell = int(shell[-2:])
        n_tot += n_shell
        if 's' in shell:
            ns += n_shell
        elif 'p' in shell:
            np += n_shell
        elif 'd' in shell:
            nd += n_shell
        elif 'f' in shell:
            nf += n_shell
    return n_tot, ns, np, nd, nf


def _feature_generate():
    """Base generator."""
    # Define atomic properties to add as features.
    prop = ['period', 'group_id', 'atomic_number', 'atomic_volume',
            'melting_point', 'boiling_point', 'density', 'electron_affinity',
            'dipole_polarizability', 'lattice_constant', 'vdw_radius',
            'covalent_radius_cordero', 'en_allen', 'mass',
            'heat_of_formation', 'block', 'econf']

    # Initialize finger vector for support elements.
    elemdict = {'Ag': [], 'Al': [], 'As': [], 'Au': [], 'B': [], 'Ba': [],
                'Be': [], 'Bi': [], 'Ca': [], 'Cd': [], 'Co': [], 'Cr': [],
                'Cs': [], 'Cu': [], 'Fe': [], 'Ga': [], 'Ge': [], 'Hf': [],
                'Hg': [], 'In': [], 'Ir': [], 'K': [], 'La': [], 'Li': [],
                'Mg': [], 'Mn': [], 'Mo': [], 'Na': [], 'Nb': [], 'Ni': [],
                'O': [], 'Os': [], 'Pb': [], 'Pd': [], 'Pt': [], 'Rb': [],
                'Re': [], 'Rh': [], 'Ru': [], 'Sb': [], 'Sc': [], 'Si': [],
                'Sn': [], 'Sr': [], 'Ta': [], 'Te': [], 'Ti': [], 'Tl': [],
                'V': [], 'W': [], 'Y': [], 'Zn': [], 'Zr': []}

    block2num = {'s': 1, 'p': 2, 'd': 3, 'f': 4}

    # Generate the features for all support elements.
    for e in elemdict:
        for p in prop:
            attr = [getattr(element(e), p)]
            if p is 'block':
                attr = [block2num[attr[0]]]
            elif p is 'econf':
                attr = list(_n_outer(attr[0]))
            elemdict[e] += attr
        elemdict[e].append(ground_state_magnetic_moments[atomic_numbers[e]])
    elemdict['La'][1] = 3.

    # Define the avaliable adsorbates.
    ads = {'C (graphene)': ['C'], 'CH2CH2': ['C']*2 + ['H']*4,
           'CH3CH2CH3': ['C']*3 + ['H']*8, 'CH3CH3': ['C']*2 + ['H']*6,
           'CO': ['C', 'O'], 'CO2': ['C'] + ['O']*2, 'H2O': ['H']*2 + ['O'],
           'HCN': ['H', 'C', 'N'], 'NH3': ['N'] + ['H']*3, 'NO': ['N', 'O'],
           'O2': ['O']*2, 'hfO2': ['O']}

    # Generate the summed features for all adsorbate elements.
    adsdict = {}
    for a in ads:
        adsdict[a] = list(np.zeros(len(prop)))
        if 'econf' in prop:
            adsdict[a] += [0] * 4
        for e in ads[a]:
            for r in range(len(prop)):
                attr = getattr(element(e), prop[r])
                if prop[r] is 'block':
                    attr = block2num[attr]
                if prop[r] is 'econf':
                    attr = _n_outer(attr)
                    for shell in range(len(attr)):
                        adsdict[a][r + shell] += attr[shell]
                else:
                    adsdict[a][r] += attr
            adsdict[a][-1] += ground_state_magnetic_moments[atomic_numbers[e]]

    # Define facet features.
    facetdict = {'0001': [1.], '0001step': [2.], '100': [3.], '110': [4.],
                 '111': [5.], '211': [6.], '311': [7.], '532': [8.]}

    # Define site features.
    sitedict = {'AA': [1.], 'BA': [2.], 'BB': [3.]}

    store_dict = {'adsdict': adsdict, 'facetdict': facetdict,
                  'elemdict': elemdict, 'sitedict': sitedict}

    # Save the potential feature space.
    with open('../data/feature_store.json', 'w') as featurefile:
        json.dump(store_dict, featurefile)


if __name__ == '__main__':
    _feature_generate()
