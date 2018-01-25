#!/bin/bash -eu

curl -XPOST http://catappdatabase.herokuapp.com/graphql --data 'query=
{catapp(first: 100, search:"oxygen evolution") {
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
}}'
