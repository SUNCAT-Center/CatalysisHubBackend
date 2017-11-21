"""
API for GraphQL enhanced queries against catapp and ase-db database

Some Examples:


- Filter by reactants and products from catapp:
    {catapp(reactants: "OH", products: "H2O") {
      edges {
        node {
  	  Reaction
          reactionEnergy
          activationEnergy
        }
      }
    }}

   
- Author-name from catapp:
    {catapp(publication_Authors: "~Bajdich") {
      edges {
        node {
          chemicalComposition
          Reaction
          reactionEnergy
        }
      }
    }}

- Full text search in catapp (title, authors, year, reactants and products ):
    {catapp(search: "oxygen evolution bajdich 2017 OOH") {
      edges {
        node {
          Reaction      
	  PublicationTitle
          PublicationAuthors
          year
        }
      }
    }}

- Author-name from ase-db:
    {textKeys(key: "publication_authors", value: "~Bajdich") {
      edges {
        node {
          systems {
            energy
            keyValuePairs
          }
        }
      }
    }}

- Get all distinct DOIs
   {textKeys(key: "publication_doi", distinct: true) {
      edges {
        node {
          key
          value
        }
      }
    }}


- Get all entries published since (and including) 2015
    allowed comparisons
{
  numberKeys(key: "publication_year", value: 2015, op: "ge") {
    edges {
      node {
        systems {
          keyValuePairs
        }
      }
    }
  }
}

"""

# global imports
import re
import json
import graphene
import graphene.relay
import graphene_sqlalchemy
import sqlalchemy
import six

# local imports
import models

class Catapp(graphene_sqlalchemy.SQLAlchemyObjectType):

    class Meta:
        model = models.Catapp
        interfaces = (graphene.relay.Node, )

class System(graphene_sqlalchemy.SQLAlchemyObjectType):

    class Meta:
        model = models.System
        interfaces = (graphene.relay.Node, )


class NumberKeyValue(graphene_sqlalchemy.SQLAlchemyObjectType):

    class Meta:
        model = models.NumberKeyValue
        interfaces = (graphene.relay.Node, )


class TextKeyValue(graphene_sqlalchemy.SQLAlchemyObjectType):

    class Meta:
        model = models.TextKeyValue
        interfaces = (graphene.relay.Node, )


class Information(graphene_sqlalchemy.SQLAlchemyObjectType):

    class Meta:
        model = models.Information
        interfaces = (graphene.relay.Node, )


class Key(graphene_sqlalchemy.SQLAlchemyObjectType):

    class Meta:
        model = models.Key
        interfaces = (graphene.relay.Node, )


class Species(graphene_sqlalchemy.SQLAlchemyObjectType):

    class Meta:
        model = models.Species
        interfaces = (graphene.relay.Node, )


class FilteringConnectionField(graphene_sqlalchemy.SQLAlchemyConnectionField):
    RELAY_ARGS = ['first', 'last', 'before', 'after']
    SPECIAL_ARGS = ['distinct', 'op', 'jsonkey']

    @classmethod
    def get_query(cls, model, info, **args):
        from sqlalchemy import or_
        query = super(FilteringConnectionField, cls).get_query(model, info)
        distinct_filter = False  # default value for distinct
        op = 'eq'
        jsonop = None
        jsonkey = None
        jsonop = None
        ALLOWED_OPS = ['gt', 'lt', 'le', 'ge', 'eq', 'ne',
                       '=',  '>',  '<',  '>=', '<=', '!=']
        ALLOWED_JSON_OPS = ['->','->>', '@>', '<@', '?',
                            '?|', '?&', '||', '-', '#-']
        # print("\n\nMODEL:: {model}".format(**locals()))
        # print(dir(model))
        for field, value in args.items():
            if field == 'distinct':
                distinct_filter = value
            elif field == 'op':
                if value in ALLOWED_OPS:
                    op = value
                    #print op
            elif field == 'jsonop':
                if value in ALLOWED_JSON_OPS:
                    jsonop = value
            elif field == 'jsonkey':
                jsonkey = value

        for field, value in args.items():
            if field not in (cls.RELAY_ARGS + cls.SPECIAL_ARGS):
                if '__' in field:  # JSON
                    field, key = field.split('__')
                    column = getattr(model, field, None)[key].astext
                else:
                    column = getattr(model, field, None)

                if field == "search":
                    from sqlalchemy.sql.expression import cast
                    reactant_string = cast(model.reactants, sqlalchemy.String)
                    product_string = cast(model.products, sqlalchemy.String)
                    reaction_string = sqlalchemy.sql.expression.func.replace(sqlalchemy.sql.expression.func.replace(reactant_string + product_string, 'gas', ''), 'star', '')
                    author_string = model.publication["authors"].astext
                    title_string = model.publication["title"].astext
                    year = model.publication["year"].astext
                    search_string = title_string + " " + author_string + " " + reaction_string \
                                    + " " + year
                    ts_vector = sqlalchemy.sql.expression.func.to_tsvector(search_string)

                    query = query.filter(ts_vector.match("'{}'".format(value)))
                    continue
                    
                if str(column.type) == "JSONB":
                    if jsonkey is not None:  
                        column = getattr(model, field, None)[jsonkey].astext
                    else:
                        column = getattr(model, field, None)
                        query = query.filter(column.has_key(value))
                        continue
                        
                if isinstance(value, six.string_types) and value.startswith("~"):
                    search_string = '%' + value[1:] + '%'
                    if distinct_filter:
                        query = query.filter(
                            column\
                            .ilike(search_string)) \
                            .distinct(column) \
                            .group_by(column)
                    else:
                        query = query.filter(
                            column.ilike(search_string))
                else:
                    if distinct_filter:
                        query = query.filter(column == value).distinct(
                            getattr(model, field)).group_by(getattr(model, field))
                    else:
                        if op in ['ge', '>=']:
                            query = query.filter(column >= value)
                        elif op in ['gt', '>']:
                            query = query.filter(column > value)
                        elif op in ['lt', '<']:
                            query = query.filter(column < value)
                        elif op in ['le', '<=']:
                            query = query.filter(column <= value)
                        elif op in ['ne', '!=']:
                            query = query.filter(column != value)
                        else:
                            query = query.filter(column == value)
                            
        return query


def get_filter_fields(model):
    """Generate filter fields (= comparison)
    from graphene_sqlalcheme model
    """

    publication_keys = ['publisher', 'doi', 'title', 'journal', 'authors', 'year']
    filter_fields = {}
    for column_name in dir(model):
        #print('FF {model} => {column_name}'.format(**locals()))
        if not column_name.startswith('_') \
                and not column_name in ['metadata', 'query', 'cifdata']:
            column = getattr(model, column_name)
            column_expression = column.expression
            # print(repr(column_expression))
            if '=' in str(column_expression):  # filter out foreign keys
                continue
            elif column_expression is None:  # filter out hybrid properties
                continue
            elif not ('<' in repr(column_expression) and '>' in repr(column_expression)):
                continue

            #column_type = repr(column_expression).split(',')[1].strip(' ()')
            column_type = re.split('\W+', repr(column_expression))

            column_type = column_type[2]
            if column_type == 'Integer':
                filter_fields[column_name] = getattr(graphene, 'Int')()
            elif column_type == 'JSONB':
                filter_fields[column_name] = getattr(graphene, 'String')()
                if column_name == 'publication':
                    for key in publication_keys:
                        filter_fields['publication__' + key] = getattr(graphene, 'String')()
            else:
                filter_fields[column_name] = getattr(graphene, column_type)()
    # always add a distinct filter
    filter_fields['distinct'] = graphene.Boolean()
    filter_fields['op'] = graphene.String()
    filter_fields['search'] = graphene.String()
    filter_fields['jsonkey'] = graphene.String()
    #print('FILTER!')
    #print(filter_fields)
    return filter_fields


class Query(graphene.ObjectType):
    node = graphene.relay.Node.Field()
    information = FilteringConnectionField(
        Information, **get_filter_fields(models.Information))
    systems = FilteringConnectionField(
        System, **get_filter_fields(models.System))
    species = FilteringConnectionField(
        Species, **get_filter_fields(models.Species))
    key = FilteringConnectionField(Key, **get_filter_fields(models.Key))
    text_keys = FilteringConnectionField(
        TextKeyValue, **get_filter_fields(models.TextKeyValue))
    number_keys = FilteringConnectionField(
        NumberKeyValue, **get_filter_fields(models.NumberKeyValue))
    catapp = FilteringConnectionField(
        Catapp, **get_filter_fields(models.Catapp))



schema = graphene.Schema(
    query=Query, types=[System, Species, TextKeyValue, NumberKeyValue, Key, Catapp],)
