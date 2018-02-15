ROOT_URL = 'http://localhost:3000'

def app_root_route():
    import app
    import requests
    #with app.app.run() as server:
        #requests.get('{ROOT_URL}/')



def catapp_has_activation_energy_test():
    import models
    catapp = models.Catapp()
    if not hasattr(catapp, 'activation_energy'):
        raise TypeError('catapp has no attribute activation_energy')

def catapp_has_ase_ids_test():
    import models
    catapp = models.Catapp()
    if not hasattr(catapp, 'ase_ids'):
        raise TypeError('catapp has no attribute ase_ids')

def catapp_has_chemical_composition_test():
    import models
    catapp = models.Catapp()
    if not hasattr(catapp, 'chemical_composition'):
        raise TypeError('catapp has no attribute chemical_composition')

def catapp_has_chemical_composition_test():
    import models
    catapp = models.Catapp()
    if not hasattr(catapp, 'chemical_composition'):
        raise TypeError('catapp has no attribute chemical_composition')

 
def catapp_has_dft_functional_test():
    import models
    catapp = models.Catapp()
    if not hasattr(catapp, 'dft_functional'):
        raise TypeError('catapp has no attribute dft_functional')

 
def catapp_has_doi_test():
    import models
    catapp = models.Catapp()
    if not hasattr(catapp, 'doi'):
        raise TypeError('catapp has no attribute doi')

 
def catapp_has_facet_test():
    import models
    catapp = models.Catapp()
    if not hasattr(catapp, 'facet'):
        raise TypeError('catapp has no attribute facet')

 
def catapp_has_id_test():
    import models
    catapp = models.Catapp()
    if not hasattr(catapp, 'id'):
        raise TypeError('catapp has no attribute id')

 
def catapp_has_metadata_test():
    import models
    catapp = models.Catapp()
    if not hasattr(catapp, 'metadata'):
        raise TypeError('catapp has no attribute metadata')

 
def catapp_has_products_test():
    import models
    catapp = models.Catapp()
    if not hasattr(catapp, 'products'):
        raise TypeError('catapp has no attribute products')

 
def catapp_has_publication_test():
    import models
    catapp = models.Catapp()
    if not hasattr(catapp, 'publication'):
        raise TypeError('catapp has no attribute publication')

 
def catapp_has_reactants_test():
    import models
    catapp = models.Catapp()
    if not hasattr(catapp, 'reactants'):
        raise TypeError('catapp has no attribute reactants')

 
def catapp_has_reaction_energy_test():
    import models
    catapp = models.Catapp()
    if not hasattr(catapp, 'reaction_energy'):
        raise TypeError('catapp has no attribute reaction_energy')

 
def catapp_has_sites_test():
    import models
    catapp = models.Catapp()
    if not hasattr(catapp, 'sites'):
        raise TypeError('catapp has no attribute sites')

 
def catapp_has_surface_composition_test():
    import models
    catapp = models.Catapp()
    if not hasattr(catapp, 'surface_composition'):
        raise TypeError('catapp has no attribute surface_composition')

 
def catapp_has_year_test():
    import models
    catapp = models.Catapp()
    if not hasattr(catapp, 'year'):
        raise TypeError('catapp has no attribute year')
