#!/usr/bin/env python

import requests
import pprint

root = 'http://catappdatabase.herokuapp.com/graphql'
pprint.pprint(requests.post(root, {'query': """{catapp(first: 100, search:"oxygen evolution") {
  totalCount
  edges {
    node {
      Reaction reactionEnergy
      chemicalComposition
      surfaceComposition
      PublicationAuthors      
      PublicationTitle
    }
  }
}}"""}).json())
