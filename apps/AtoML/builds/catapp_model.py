"""Run script for GP."""
from __future__ import absolute_import
from __future__ import division

import time
import pickle
import numpy as np

from atoml.regression import GaussianProcess

train_data = np.load('train_data/catapp_features.npy')
train_target = np.load('train_data/catapp_targets.npy')

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
    train_fp=train_data, train_target=train_target, kernel_dict=kdict,
    regularization=1e-1, optimize_hyperparameters=True, scale_data=True
)
print('trained {}'.format(time.time() - st))

with open('models/catapp_gp_model.pickle', 'wb') as model:
    pickle.dump(gp, model, protocol=pickle.HIGHEST_PROTOCOL)
