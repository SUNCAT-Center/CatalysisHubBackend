Tutorials
=========
GraphQL
-------

These tutorials will focus on how to use the GraphQL interface to the database. You might also want to read the documentation at 
     {publications(first:10) {
       edges {
         node {
           id
	   title
	   pubId
	   authors
	   reactions
	   }
	 }
     }}

   or use the `pubId` field to query directly on the reactions table to make additional queries::
     
     reactions(pubId: "")}

2) Using the :code::(`pubID: )` solution above, list all the distinct
   a) reactions
   b) surfaces
   from Julia's publication.

3) Chose one of Julia's reactions and find the `aseId` of the empty slab. Hint: It has :code::`"name"="star"` in the `reactionSystems` table.
   Copy the aseId and use it to find all the reactions that are linked to that particular empty slab.

   

   

  

	      
