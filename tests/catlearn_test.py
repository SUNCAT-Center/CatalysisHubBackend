

def catlearn_test():
    import numpy as np
    from ase.build import fcc111, add_adsorbate
    from apps.catlearn.atomistic import predict_catkit_demo

    images = []
    atoms = fcc111('Pt', (2, 2, 3))
    add_adsorbate(atoms, 'C', 2.)
    atoms.info['key_value_pairs'] = {'species': 'C'}
    tags = atoms.get_tags()
    tags[-1] = -1
    tags = atoms.set_tags(tags)

    images.append(atoms)
    atoms = fcc111('Ag', (2, 2, 3))
    add_adsorbate(atoms, 'C', 2.)
    atoms.info['key_value_pairs'] = {'species': 'C'}
    tags = atoms.get_tags()
    tags[-1] = -1
    tags = atoms.set_tags(tags)
    images.append(atoms)

    # Make prediction.
    dictionary = predict_catkit_demo(images)

    assert not np.isnan(dictionary['mean']).all()
    assert not np.isnan(dictionary['uncertainty']).all()
