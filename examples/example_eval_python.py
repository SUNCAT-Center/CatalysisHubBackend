#!/usr/bin/env python
import requests
import pprint

# import needed for ASE constructor
import numpy as np
from ase.atoms import Atoms

root = 'http://catappdatabase.herokuapp.com/graphql'

query = requests.post(
    root,
    {'query':
     """{catapp(first: 10, search:"boes") {
     edges {
       node {
	 Systems {
	     # Positions
	     # Cell
             # Chemicalsymbols
             InputFile(format: "py")
	 }
       }
     }
}}"""})

for edge in query.json()['data']['catapp']['edges']:
    for system in edge['node']['Systems']:
        images = eval(('='.join(system['InputFile'].split('=')[1:])))
        print(images[0].get_chemical_symbols())
