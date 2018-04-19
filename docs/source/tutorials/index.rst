Tutorials
=========
GraphQL
-------

These tutorials will focus on how to use the GraphQL interface to the database.
Go to http://api.catalysis-hub.org/graphql to get started.

Getting started
...............

Type your query in the left panel. In order to perform queries on the `reactions` table try this::
  
   {reactions(first:2)}

And type `command + return` to see the result in the right panel. This should return the `id` of the first two reactions in the database. Notice that the left hand side is updated as well. 


Now try to add more columns after `id` and see what is returned. For example::
  
  {reactions(first:2) {
    edges {
      node {
        id
        chemicalComposition
     	reactionEnergy	
      }
    }
  }}

 
For a complete list of all the tables in the database, and the asociated columns, see the `Docs` tab to the right. There is also a schema overview posted at  http://docs.catalysis-hub.org/reference/schema/ . 

In order to make selections on the result, add more fields after `::(first:2)`. For example::
  
   {reactions(first:2, reactants: "CO", chemicalComposition: "Pt")}


Searching for publications
..........................

1) Find all titles and doi's from publications with year=2017.

2) How many publications are there with year>2015?

3) How many publications are authored by Thomas Bligaard? Hint: use the pubtexsearch field.
   You can list the total number of results using the `totalCount` field::
     
     {publications {
       totalCount
       edges {
         node {
           id
           authors
         }
       }
     }}


   Verify that you get the same result by using :code:`(authors: "~bligaard")`

4) Find Michal Bajdich's paper with Oxygen Evolution in the title


Using the reactions table
.........................
1) Find the number of reactions with H2O on the left hand side and OH on the right hand side.
   How many distinct reactions does that give rise to?
   What happens when you add the state (star or gas) to your query?
   What happens when you add :code:`chemicalComposition: "~"`


 

Cathub cli tutorials
--------------------

   	      
	      
