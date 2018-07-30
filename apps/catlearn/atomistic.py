"""
Attach CatLearn adsorption energy predictions to CatKitDemo.
"""
import numpy as np

from sklearn.preprocessing import Imputer

from catlearn.fingerprint.adsorbate_prep import autogen_info
from catlearn.fingerprint.setup import FeatureGenerator, default_fingerprinters
from catlearn.regression.gpfunctions import io as gp_io


model_fname = 'apps/catlearn/models/metals_catlearn_gp'
clean_index_name = 'apps/catlearn/train_data/metals_clean_index.npy'
clean_median = 'apps/catlearn/train_data/metals_clean_feature_median.npy'


def predict_catkit_demo(images):
    """Return a prediction of adsorption energies for structures generated with
    CatKitDemo.

    Parameters
    ----------
    images : list
        List of atoms objects representing adsorbate-surface structures.
    model : str
        Path and filename of Catlearn model pickle.
    """
    images = autogen_info(images)

    gen = FeatureGenerator(nprocs=1)
    train_fpv = default_fingerprinters(gen, 'adsorbates')
    train_fpv = [gen.mean_chemisorbed_atoms,
                 gen.count_chemisorbed_fragment,
                 gen.count_ads_atoms,
                 gen.count_ads_bonds,
                 gen.ads_av,
                 gen.ads_sum,
                 gen.bulk,
                 gen.term,
                 gen.strain,
                 gen.mean_surf_ligands,
                 gen.mean_site,
                 gen.median_site,
                 gen.max_site,
                 gen.min_site,
                 gen.sum_site,
                 gen.generalized_cn,
                 gen.en_difference_ads,
                 gen.en_difference_chemi,
                 gen.en_difference_active,
                 gen.db_size,
                 gen.delta_energy]
    matrix = gen.return_vec(images, train_fpv)

    gp = gp_io.read(model_fname)
    feature_index = np.load(clean_index_name)
    clean_feature_median = np.load(clean_median)

    impute = Imputer(missing_values="NaN", strategy='median')
    impute.statistics_ = clean_feature_median
    new_data = impute.transform(matrix[:, feature_index])

    prediction = gp.predict(new_data,
                            get_validation_error=False,
                            get_training_error=False,
                            uncertainty=True)

    return prediction['prediction'], prediction['uncertainty']
