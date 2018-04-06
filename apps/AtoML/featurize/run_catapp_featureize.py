from __future__ import absolute_import
from __future__ import division

import csv
import re
import numpy as np

from catapp_user import return_features
from atoml.preprocess.clean_data import clean_variance, clean_infinite

data_path = 'train_data/'


class AttrDict(dict):
    def __init__(self, *args, **kwargs):
        super(AttrDict, self).__init__(*args, **kwargs)
        self.__dict__ = self


# Read in CatApp data.
cafile = open('raw_data/catappdata.csv', 'r')
ca = csv.DictReader(cafile)
calist = [AttrDict(c) for c in ca]

# Parse the output to generate descriptor dict.
reactionlist = [c for c in calist if (c.b == '*') and c.surface[:2] != 'HH' and
                c.a != 'hfH2' and c.a != 'H' and float(c.reaction_energy) < 20]

print('data length {}'.format(len(reactionlist)))


def parse(surf):
    """Parsing the surface."""
    return re.search(
        '([A-Z][a-z]?)?([0-9])?([A-Z][a-z]?)? ?\(([0-9a-z]+)\) ?([A-Z]+)?',
        re.sub(
            '([A-Z][a-z]?)([A-Z][a-z]?)([0-9])( ?\([0-9a-z]+\) ?)([A-Z])?([A-Z])?',
            r'\2\3\1\4\6\5', surf)).groups()


for r in reactionlist:
    m1, conc, m2, facet, site = parse(r.surface)
    r.facet = facet
    if conc is None:
        r.conc = 0.5
    if m2 is None:
        m2 = m1
    if m1 <= m2:
        r.m1 = m1
        r.m2 = m2
        if conc is '3':
            r.conc = 0.25
    else:
        r.m1 = m2
        r.m2 = m1
        if conc is '3':
            r.conc = 0.75
        if site is 'AB':
            site = 'BA'
        elif site is 'BA':
            site = 'AB'
        elif site is 'AA':
            site = 'BB'
        elif site is 'BB':
            site = 'AA'
    if site is None:
        site = 'AA'
    r.site = site

for r in reactionlist:
    m1, conc, m2, facet, site = parse(r.surface)
    r.facet = facet
    if conc is None:
        if m2 is None:
            r.conc = 0.5
        else:
            r.conc = 0.5
    if m2 is None:
        m2 = m1
    r.m1 = m1
    r.m2 = m2
    if conc is '3':
        r.conc = 0.75
    if site is None:
        site = 'AA'
    r.site = site

syss = reactionlist

# Generate the fingreprints for all systems.
trainfingers = np.asarray([return_features(sys) for sys in syss])
train_name = np.asarray([sys['surface'] + ' ' + sys['a'] for sys in syss])

# Get the target values for training and test.
for prop in ['reaction_energy']:
    trainval = [float(getattr(sys, prop)) for sys in syss]

# Clean up the data
data_dict0 = clean_infinite(trainfingers)
print(data_dict0['index'])
data_dict1 = clean_variance(data_dict0['train'])
print(data_dict1['index'])
allfingers = data_dict1['train']

# Save all the data.
print('Saving', np.shape(allfingers), 'all data matrix.')
np.save(file=data_path + 'catapp_features.npy', arr=allfingers,
        allow_pickle=True, fix_imports=True)
np.save(file=data_path + 'catapp_targets.npy', arr=trainval,
        allow_pickle=True, fix_imports=True)

np.save(file=data_path + 'catapp_name.npy', arr=train_name,
        allow_pickle=True, fix_imports=True)
