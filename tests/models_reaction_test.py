ROOT_URL = 'http://localhost:3000'

def app_root_route():
    import app
    import requests
    #with app.app.run() as server:
        #requests.get('{ROOT_URL}/')

def reaction_has_activation_energy_test():
    import models
    reaction = models.Reaction()
    if not hasattr(reaction, 'activation_energy'):
        raise TypeError('reaction has no attribute activation_energy')

    
def reaction_has_pub_id_test():
    import models
    reaction = models.Reaction()
    if not hasattr(reaction, 'pub_id'):
        raise TypeError('reaction has no attribute pub_id')

    
def reaction_has_chemical_composition_test():
    import models
    reaction = models.Reaction()
    if not hasattr(reaction, 'chemical_composition'):
        raise TypeError('reaction has no attribute chemical_composition')

    
def reaction_has_dft_functional_test():
    import models
    reaction = models.Reaction()
    if not hasattr(reaction, 'dft_functional'):
        raise TypeError('reaction has no attribute dft_functional')

 
def reaction_has_facet_test():
    import models
    reaction = models.Reaction()
    if not hasattr(reaction, 'facet'):
        raise TypeError('reaction has no attribute facet')

 
def reaction_has_id_test():
    import models
    reaction = models.Reaction()
    if not hasattr(reaction, 'id'):
        raise TypeError('reaction has no attribute id')

 
def reaction_has_metadata_test():
    import models
    reaction = models.Reaction()
    if not hasattr(reaction, 'metadata'):
        raise TypeError('reaction has no attribute metadata')

 
def reaction_has_products_test():
    import models
    reaction = models.Reaction()
    if not hasattr(reaction, 'products'):
        raise TypeError('reaction has no attribute products')

  
def reaction_has_reactants_test():
    import models
    reaction = models.Reaction()
    if not hasattr(reaction, 'reactants'):
        raise TypeError('reaction has no attribute reactants')

 
def reaction_has_reaction_energy_test():
    import models
    reaction = models.Reaction()
    if not hasattr(reaction, 'reaction_energy'):
        raise TypeError('reaction has no attribute reaction_energy')

 
def reaction_has_sites_test():
    import models
    reaction = models.Reaction()
    if not hasattr(reaction, 'sites'):
        raise TypeError('reaction has no attribute sites')

 
def reaction_has_surface_composition_test():
    import models
    reaction = models.Reaction()
    if not hasattr(reaction, 'surface_composition'):
        raise TypeError('reaction has no attribute surface_composition')

    
def reaction_has_username_test():
    import models
    reaction = models.Reaction()
    if not hasattr(reaction, 'username'):
        raise TypeError('reaction has no attribute username')

 
