"""Run script for GP."""
from __future__ import absolute_import
from __future__ import division

import time
import numpy as np

from catlearn.regression import GaussianProcess
from catlearn.regression.gpfunctions import io as gp_io

train_data = np.load('apps/catlearn/train_data/catapp_features.npy')
train_target = np.load('apps/catlearn/train_data/catapp_targets.npy')
print(np.shape(train_data), np.shape(train_target))

kdict = {
    'k1': {
        'type': 'linear', 'scaling': 1.,
    },
    'k2': {
        'type': 'constant', 'const': 1.,
    },
    'k3': {
        'type': 'gaussian', 'width': 1., 'scaling': 1., 'dimension': 'single'
    },
    'k4': {
        'type': 'quadratic', 'slope': 1., 'degree': 1., 'scaling': 1.,
        'dimension': 'single',
    },
    'k5': {
        'type': 'laplacian', 'width': 1., 'scaling': 1.,
        'dimension': 'single'
    },
}

st = time.time()
print('train model')
gp = GaussianProcess(
    train_fp=train_data[:200, :], train_target=train_target[:200],
    kernel_dict=kdict,
    regularization=1e-1, optimize_hyperparameters=True, scale_data=True)
print('trained {}'.format(time.time() - st))

gp_io.write('catapp_catlearn_gp', gp)

# with open('apps/catlearn/models/catapp_catlearn_gp.pickle', 'wb') as model:
#     pickle.dump(gp, model, protocol=pickle.HIGHEST_PROTOCOL)
