"""Run script for GP."""
from __future__ import absolute_import
from __future__ import division

import time
import numpy as np

from sklearn.preprocessing import Imputer

from catlearn.preprocess.clean_data import clean_infinite, clean_variance
from catlearn.regression import GaussianProcess
from catlearn.regression.gpfunctions import io as gp_io


data_fname = 'apps/catlearn/raw_data/metals_train.npy'
model_fname = 'apps/catlearn/models/metals_catlearn_gp'
clean_index_name = 'apps/catlearn/train_data/metals_clean_index.npy'
clean_mean = 'apps/catlearn/train_data/metals_clean_feature_mean.npy'

data = np.load(data_fname)
train_target = data[:, -1]

finite = clean_infinite(data[:, :-1])
informative = clean_variance(data[:, :-1])

clean_index = np.intersect1d(finite['index'],
                             informative['index'])

train_data = data[:, clean_index]

impute = Imputer(missing_values="NaN", strategy='mean')
impute.fit(train_data)
clean_feature_median = np.save(clean_mean, impute.statistics_)

print(np.shape(train_data), np.shape(train_target))

kdict = {'gk': {'type': 'gaussian',
                'width': 3.,
                'scaling': 1.0,
                }}


st = time.time()
print('Training model...')
gp = GaussianProcess(
    train_fp=train_data[:1000, :], train_target=train_target[:1000],
    kernel_dict=kdict,
    regularization=1e-1, optimize_hyperparameters=True, scale_data=True)
print('Trained model in {}'.format(time.time() - st))

gp.update_data(train_data, train_target=train_target)


clean_index = np.save(clean_index_name, clean_index)

gp_io.write(model_fname, gp)
