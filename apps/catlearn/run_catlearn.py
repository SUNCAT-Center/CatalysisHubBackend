"""Flask app for catlearn-CatApp model."""
import flask
import numpy as np
from flask import Blueprint

from apps.catlearn.featurize.catapp_user import return_features
from catlearn.regression.gpfunctions import io as gp_io

catlearn_blueprint = Blueprint('catlearn', __name__)


@catlearn_blueprint.route('/', methods=['GET', 'POST'])
def run_catlearn_app():
    """The actual app to predict and generate output."""
    data = flask.request.json
    # Add some default values in case no data is provided.
    if data is None:
        data = {
            "m1": "Pt",
            "m2": "Pd",
            "facet": "111",
            "a": "hfO2",
            "conc": "0.5",
            "site": "AA"
        }

    # Compile the features for the tests data and generate output.
    features, output = _get_output(data)
    return_dict = {'input': data, 'features': features, 'output': output}
    return_dict = flask.jsonify(**return_dict)

    return return_dict


def _get_model():
    """Load the generated model."""
    model = gp_io.read('apps/catlearn/models/catapp_catlearn_gp')
    return model


def _get_output(data):
    """Make the prediction on the input system."""
    # Load the GP model.
    model = _get_model()

    # Load the features for the test system.
    features = np.array([return_features(data)])
    features = np.delete(features, [28, 33, 50, 55, 19], axis=1).tolist()

    # Make the predictions.
    pred = model.predict(test_fp=features, uncertainty=True)
    result = {'energy': round(float(pred['prediction'][0]), 3),
              'uncertainty': round(float(pred['uncertainty'][0]), 3)}

    return features, result
