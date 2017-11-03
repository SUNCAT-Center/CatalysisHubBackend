#!/usr/bin/env python

import sys


def to_camel_case(snake_str):
    components = snake_str.split('_')
    # We capitalize the first letter of each component except the first one
    # with the 'title' method and join them together.
    return components[0].title() + "".join(x.title() for x in components[1:])


def to_snake_case(name):
    split_name = list(name)
    for c in range(len(split_name)):
        if split_name[c].isupper() and c != 0 and split_name[c - 1] != '_':
            split_name.insert(c, '_')
            c += 1

    return ''.join(split_name).lower()


def main(infile, options, outfile=sys.stdout, ):

    table_names = []

    old_table_catalog = None
    old_table_schema = None
    old_table_name = None
    old_column_name = None
    old_ordinal_position = None
    old_column_default = None
    old_is_nullable = None
    old_data_type = None
    old_character_maximum_length = None
    old_character_octet_length = None
    old_numeric_precision = None
    old_numeric_scale = None
    old_datetime_precision = None
    old_character_set_name = None
    old_collation_name = None
    old_column_type = None
    old_column_key = None
    old_extra = None
    old_privileges = None
    old_column_comment = None
    old_generation_expression = None

    for i, line in enumerate(infile):
            # print(line.split('\t'))
        if i == 0:
            db_name = line.strip()
            outfile.write("""
# global imports
import graphene
import graphene.types.datetime
import graphene.relay
import graphene.types.json
import graphene_sqlalchemy
import json
import os
import re
import six
import sqlalchemy
import sqlalchemy.ext.declarative
import sqlalchemy.types

try:
    import io as StringIO
except:
    # Fallback solution for python2.7
    import StringIO

import numpy as np

import json
import sqlalchemy as sqla
from sqlalchemy.ext import mutable
from sqlalchemy.ext.hybrid import hybrid_property

# more unstable imports
import ase.atoms
import ase.db.sqlite
import ase.io



# set to local database path
engine = sqlalchemy.create_engine(
    'mysql+mysqldb://' + os.environ['MYSQL_USER'] + ':' + os.environ['MYSQL_PW'] +  '@localhost/{db_name}', convert_unicode=True)

db_session = sqlalchemy.orm.scoped_session(sqlalchemy.orm.sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
))


Base = sqlalchemy.ext.declarative.declarative_base()
Base.query = db_session.query_property()

        """.format(**locals()))
            continue
        elif i == 1:
            continue

        table_catalog, \
                table_schema, \
                table_name, \
                column_name, \
                ordinal_position, \
                column_default, \
                is_nullable, \
                data_type, \
                character_maximum_length, \
                character_octet_length, \
                numeric_precision, \
                numeric_scale, \
                datetime_precision, \
                character_set_name, \
                collation_name, \
                column_type, \
                column_key, \
                extra, \
                privileges, \
                column_comment, \
                generation_expression \
                = line.split(
            '\t')

        # SKIP A TABLE NAMED META_DATA
        if table_name == 'meta_data':
            continue

        # HERE BE DRAGONS
        if table_name != old_table_name:
            outfile.write('\n\nclass {0}(Base):\n    __tablename__ = \'{1}\'\n'.format(
                to_camel_case(table_name), table_name))
            table_names.append(table_name)

        mapping = {
            'int': 'Integer',
            'datetime': 'Date',
            'float': 'Float',
            'double': 'Float',
            'tinyint': 'Integer',
            'smallint': 'Integer',
            'char': 'String',
            'varchar': 'String',
            'text': 'String',
            'longtext': 'String',
        }

        value = mapping.get(data_type, None)
        if value:
            # if column_key == 'PRI':
            if table_name != old_table_name:
                primary_string = 'primary_key=True, '
            else:
                primary_string = ''
            #print(column_key, primary_string)
            outfile.write(
                '    {column_name} = sqlalchemy.Column(sqlalchemy.{value}, {primary_string})\n'.format(**locals()))
        else:
            print(len(line.split('\t')), line.split())

        # HERE END DRAGONS
        old_table_catalog = table_catalog
        old_table_schema = table_schema
        old_table_name = table_name
        old_column_name = column_name
        old_ordinal_position = ordinal_position
        old_column_default = column_default
        old_is_nullable = is_nullable
        old_data_type = data_type
        old_character_maximum_length = character_maximum_length
        old_character_octet_length = character_octet_length
        old_numeric_precision = numeric_precision
        old_numeric_scale = numeric_scale
        old_datetime_precision = datetime_precision
        old_character_set_name = character_set_name
        old_collation_name = collation_name
        old_column_type = column_type
        old_column_key = column_key
        old_extra = extra
        old_privileges = privileges
        old_column_comment = column_comment
        old_generation_expression = generation_expression

    for table_name in table_names:
        camel_case = to_camel_case(table_name)
        outfile.write(('\n\nclass {camel_case}Node(graphene_sqlalchemy.SQLAlchemyObjectType):'
                       '\n\n    class Meta:'
                       '\n        model = {camel_case}'
                       '\n        interfaces = (graphene.relay.Node, )').format(**locals()))

    outfile.write("""


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
        for field, value in sorted(args.items()):
            if field == 'distinct':
                distinct_filter = value
            elif field == 'op':
                if value in ALLOWED_OPS:
                    op = value

            if field not in (cls.RELAY_ARGS + cls.SPECIAL_ARGS):
                if isinstance(value, six.string_types) and value.startswith("~"):
                    search_string = '%' + value[1:] + '%'
                    if distinct_filter:
                        query = query.filter(
                            getattr(model, field, None) \\
                            .ilike(search_string)) \\
                            .distinct(getattr(model, field, None)) \\
                            .group_by(getattr(model, field, None))
                    else:
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


def _get_filter_fields(model):
    \"\"\"Generate filter fields (= comparison)
    from graphene_sqlalcheme model
    \"\"\"
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
            elif column_type == 'Date':
                filter_fields[column_name] = getattr(graphene.types.datetime, 'DateTime')()
            else:
                filter_fields[column_name] = getattr(graphene, column_type)()
# always add a distinct filter
    filter_fields['distinct'] = graphene.Boolean()
    filter_fields['op'] = graphene.String()

    return filter_fields


class Query(graphene.ObjectType):
""")
    sys.stdout.write("    node = graphene.relay.Node.Field()\n")
    for table_name in table_names:
        snake_table_name = to_snake_case(table_name)
        class_table_name = to_camel_case(table_name)
        #print("@@@\n@@@\n@@@ {table_name}".format(**locals()))
        #print("@@@ {class_table_name}".format(**locals()))
        #print("@@@ {snake_table_name}".format(**locals()))
        sys.stdout.write(
            "    {snake_table_name} = FilteringConnectionField({class_table_name}Node, **_get_filter_fields({class_table_name}))\n".format(**locals()))

    table_names_list = '[' + \
        ', '.join([to_camel_case(x) + 'Node' for x in table_names]) + ']'
    sys.stdout.write(
        '\n\nschema = graphene.Schema(query=Query, types={table_names_list},)\n'.format(**locals()))


if __name__ == '__main__':
    import optparse
    parser = optparse.OptionParser()
    parser.add_option('-d', '--db-name', dest='db_name', type=str, default='')
    options, args = parser.parse_args()
    if len(args) < 1:
        raise UserWarning("""Expected schema drop file path as input. Generate it using MyQL CLI with\n\n
        DB_NAME=<your_db_name>
        mysql -u root -p -A  < <(echo "SELECT * FROM information_schema.columns WHERE table_schema = '${DB_NAME}'") > ${DB_NAME}_schema.txt
                """)

    if len(args) == 2:
        outfile = open(args[1], 'w')
    else:
        outfile = sys.stdout

    with open(args[0]) as infile:
        main(infile, outfile=outfile, options=options)
