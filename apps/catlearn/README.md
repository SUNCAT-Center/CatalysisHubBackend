# AtoML App

The backend for AtoML. The idea here is to have a unified environment in which we can train and serve some general models.

The backend assumes that a model has been optimized and saved previously. A query to that model is made by generating the test feature vector based on some input from the website. The simplest model will then make a prediction and quantify uncertainty.

## Requirements

*   [AtoML](https://gitlab.com/atoml/AtoML)
*   [numpy](http://www.numpy.org/)
*   [mendeleev](https://pypi.python.org/pypi/mendeleev/)

## Builds

The scripts to build the models are located in this directory. Currently, there is an example script for the old CatApp data. This will save a pickle file which can be loaded by the app to make predictions based on this early data.

## Featurize

The directory contains scripts to featurize user input data. This should be moved to AtoML at some point for greater stability and maintainability.

## Models

The saved models as a pickle file. This should be switched to the HDF5 save format in future.

## Raw Data

There is currently the original CatApp data for building a model.

## Train Data

The stored featurized dataset, target values, and names.
