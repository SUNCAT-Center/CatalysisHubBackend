"""Run script for GP."""
from __future__ import absolute_import
from __future__ import division

import time
import numpy as np

from catlearn.preprocess.clean_data import clean_infinite, clean_variance
from catlearn.regression import GaussianProcess
from catlearn.regression.gpfunctions import io as gp_io

data = np.load('apps/catlearn/raw_data/metals_train.npy')
train_target = data[:, -1]

finite = clean_infinite(data[:, :-1])
informative = clean_variance(data[:, :-1])

clean_index = np.intersect1d(finite['index'],
                             informative['index'])

train_data = data[:, clean_index]

print(np.shape(train_data), np.shape(train_target))

kdict = {'gk': {'type': 'gaussian',
                'width': 3.,
                'scaling': 1.0,
                }}


st = time.time()
print('train model')
gp = GaussianProcess(
    train_fp=train_data[:50, :], train_target=train_target[:50],
    kernel_dict=kdict,
    regularization=1e-1, optimize_hyperparameters=True, scale_data=True)
print('trained {}'.format(time.time() - st))

gp.update_data(train_data, train_target=train_target)

gp.clean_index = clean_index

gp_io.write('metals_catlearn_gp', gp)
