"""
API for GraphQL enhanced queries again ase-db database

Some Examples:

 - Filter by author-name
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

# local imports
import models
import models_catapp

class Catapp(graphene_sqlalchemy.SQLAlchemyObjectType):

    class Meta:
        model = models_catapp.Catapp
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
    SPECIAL_ARGS = ['distinct', 'op']

    @classmethod
    def get_query(cls, model, info, **args):
        query = super(FilteringConnectionField, cls).get_query(model, info)
        distinct_filter = False  # default value for distinct
        op = 'eq'
        ALLOWED_OPS = ['gt', 'lt', 'le', 'ge', 'eq', 'ne'
                       '=',  '>',  '<',  '>=', '<=', '!=']
        #print("\n\nMODEL:: {model}".format(**locals()))
        # print(dir(model))

        for field, value in sorted(args.items()):
            if field == 'distinct':
                distinct_filter = value
            elif field == 'op':
                if value in ALLOWED_OPS:
                    op = value

            if field not in (cls.RELAY_ARGS + cls.SPECIAL_ARGS):
                if type(value) is unicode and value.startswith("~"):
                    search_string = '%' + value[1:] + '%'
                    query = query.filter(
                        getattr(model, field, None).ilike(search_string))
                else:
                    if distinct_filter:
                        query = query.filter(getattr(model, field, None) == value).distinct(
                            getattr(model, field)).group_by(getattr(model, field))
                    else:
                        if op in ['ge', '>=']:
                            query = query.filter(
                                getattr(model, field, None) >= value)
                        elif op in ['gt', '>']:
                            query = query.filter(
                                getattr(model, field, None) > value)
                        elif op in ['lt', '<']:
                            query = query.filter(
                                getattr(model, field, None) < value)
                        elif op in ['le', '<=']:
                            query = query.filter(
                                getattr(model, field, None) <= value)
                        elif op in ['!=']:
                            query = query.filter(
                                getattr(model, field, None) != value)
                        else:
                            query = query.filter(
                                getattr(model, field, None) == value)
        return query


def get_filter_fields(model):
    """Generate filter fields (= comparison)
    from graphene_sqlalcheme model
    """
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
            # print(column_type)
            column_type = column_type[2]
            if column_type == 'Integer':
                filter_fields[column_name] = getattr(graphene, 'Int')()
            else:
                filter_fields[column_name] = getattr(graphene, column_type)()
    # always add a distinct filter
    filter_fields['distinct'] = graphene.Boolean()
    filter_fields['op'] = graphene.String()

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
        Catapp, **get_filter_fields(models_catapp.Catapp))

schema = graphene.Schema(
    query=Query, types=[System, Species, TextKeyValue, NumberKeyValue, Key, Catapp],)
