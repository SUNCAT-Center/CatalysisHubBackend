# AtoML App

The backend for AtoML. It assumes that a model has been optimized and saved previously.

## Usage

To run the app, use:

```shell
  $ export FLASK_APP=run_atoml.py
  $ flask run
```

To make the app publicly visible, use:

```shell
  $ flask run --host=0.0.0.0
```

## Requirements

*   [AtoML](https://gitlab.com/atoml/AtoML)
*   [numpy](http://www.numpy.org/)
*   [mendeleev](https://pypi.python.org/pypi/mendeleev/)

## Builds

The scripts to build the models are located in this directory.

## Featurize

The directory contains scripts to featurize user input data.

## Models

The saved models.

## Raw Data

There is currently the original CatApp data for building a model.

## Train Data

The stored featurized data set.
