"""Flask app for AtoML-CatApp model."""
import pickle
import numpy as np
import flask
from flask_cors import CORS

from feature_generator import return_features

app = flask.Flask(__name__)
CORS(app)


@app.route('/', methods=['GET', 'POST'])
def run_atoml_app():
    """The actual app to predict and generate output."""
    data = flask.request.json
    features, output = _get_output(data)
    return_dict = {'input': data, 'features': features, 'output': output}
    return_dict = flask.jsonify(**return_dict)

    return return_dict


def _get_model():
    """Load the generated model."""
    with open('model/gp_model_01.pickle', 'rb') as modelfile:
        model = pickle.load(modelfile)
    return model


def _get_output(data):
    """Make the prediction on the input system."""
    # Load the GP model.
    m = _get_model()

    # Load the features for the test system.
    f = return_features(data)

    # Some global scaling data generated previously.
    scale_mean = np.load(file='data/feature_mean.npy')
    scale_dif = np.load(file='data/feature_dif.npy')

    # Scale the test features.
    tfp = (np.array([f], np.float64) - scale_mean) / scale_dif

    # Make the predictions.
    pred = m.predict(test_fp=tfp, uncertainty=True)
    result = {'energy': round(pred['prediction'][0], 3),
              'uncertainty': round(pred['uncertainty'][0] * 1.97897351706, 3)}

    return list(f), result
