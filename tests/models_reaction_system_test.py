ROOT_URL = 'http://localhost:3000'

def app_root_route():
    import app
    import requests
    #with app.app.run() as server:
        #requests.get('{ROOT_URL}/')

        
def reaction_system_has_name_test():
    import models
    reaction_system = models.ReactionSystem()
    if not hasattr(reaction_system, 'name'):
        raise TypeError('reactionSystem has no attribute name')


def reaction_system_has_ase_id_test():
    import models
    reaction_system = models.ReactionSystem()
    if not hasattr(reaction_system, 'ase_id'):
        raise TypeError('reactionSystem has no attribute ase_id')


def reaction_system_has_reaction_id_test():
    import models
    reaction_system = models.ReactionSystem()
    if not hasattr(reaction_system, 'id'):
        raise TypeError('reactionSystem has no attribute id')
        
