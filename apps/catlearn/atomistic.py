"""
Attach CatLearn adsorption energy predictions to CatKitDemo.
"""
import numpy as np

from sklearn.impute import SimpleImputer

import ase.atoms

from catlearn.featurize.adsorbate_prep import autogen_info
from catlearn.featurize.setup import FeatureGenerator, default_fingerprinters
from catlearn.regression.gpfunctions import io as gp_io


model_fname = 'apps/catlearn/models/metals_catlearn_gp'
clean_index_name = 'apps/catlearn/train_data/metals_clean_index.npy'
clean_mean = 'apps/catlearn/train_data/metals_clean_feature_mean.npy'

# Load pickled Gaussian process regression model.
gp = gp_io.read(model_fname)


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
    model_ref = {'H': 'H2',
                 'O': 'H2O, H2',
                 'C': 'CH4, H2'}

    # Make list of strings showing the references.
    display_ref = []
    for atoms in images:
        try:
            initial_state = [model_ref[s] for s in
                             ase.atoms.string2symbols(
                                 atoms.info['key_value_pairs']['species'])]
        except KeyError:
            return {}
        display_ref.append(
                '*, ' + ', '.join(list(np.unique(initial_state))))

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

    feature_index = np.load(clean_index_name)
    clean_feature_mean = np.load(clean_mean)

    impute = SimpleImputer(strategy='mean')
    impute.statistics_ = clean_feature_mean
    new_data = impute.transform(matrix[:, feature_index])

    prediction = gp.predict(new_data,
                            get_validation_error=False,
                            get_training_error=False,
                            uncertainty=True)

    output = {'mean': list(prediction['prediction']),
              'uncertainty': list(prediction['uncertainty']),
              'references': display_ref}
    return output
