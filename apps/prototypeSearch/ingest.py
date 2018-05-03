#!/usr/bin/env python3.6

import os
import pprint
import sys
import time

from sqlalchemy.sql.expression import Tuple

import models
import mendeleev

# create table if it hasn't already happened
models.metadata.create_all(models.engine)
models.session.commit()



#@profile
def bulk_upsert(db, geometries):
    geometries_dict = {
            (geometry.repository, geometry.handle): geometry
                 for geometry in geometries
            }
    existing = db.Geometry.query.filter(
            Tuple(db.Geometry.repository, db.Geometry.handle).in_(
                (geometry.repository, geometry.handle)
                for geometry in geometries
                )
            )
    for each in existing.all():
        db.session.merge(geometries_dict.pop((each.repository,
                                              each.handle)))
    existing.delete(synchronize_session='fetch')

    db.session.add_all(geometries)
    db.session.commit()


#@profile
def main(filename, options):
    time0 = time.time()
    repository_name = os.path.splitext(
            os.path.basename(filename)
            )[0]

    submitted_handles = set()
    n_duplicates = 0
    n_errors = 0
    error_lines = []
    error_lines_nr = []
    duplicates = []
    geometries = []

    with open(filename) as infile:
        for i, line in enumerate(infile):
            if i == 0: print(line); continue

            fields = line.split(' | ')
            filename = (fields[0])
            data = {}

            try:
                data['repository'] = repository_name
                data['spacegroup'] = int(fields[0])
                data['n_atoms'] = int(fields[1])
                data['n_wyckoffs'] = int(fields[2])
                data['wyckoffs'] = fields[3].split()
                data['n_species'] = len(set(fields[5].split()))
                data['species'] = fields[5].split()
                data['n_parameters'] = int(fields[6])
                data['parameter_names'] = fields[7].split()
                data['prototype'] = fields[8]
                data['stoichiometry'] = data['prototype'].split('_')[0]
                data['n_permutations'] = int(fields[9])
                #data['permutations'] = fields[10]
                if len(fields) == 14:
                    data['tags'] = fields[13].lower().split()
                    data['parameters'] = list(map(lambda x: float(x), fields[12].split()))
                    data['handle'] = fields[11]
                else:
                    data['handle'] = fields[11]
                    data['parameters'] = list(map(lambda x: float(x), fields[12].split()))

                # usually affects only protein crystals
                # gives trouble in indexs
                # let's skip those for now
                if len(data['species']) >= 60:
                    continue
            except:
                print("Error in line {i}".format(**locals()))
                print("Fields")
                print(fields)
                n_errors += 1
                
                error_lines.append(fields)
                error_lines_nr.append(i + 1)
                continue
                #raise

            #data['a_param'] = fields[7].split()[0]

            if options.test:
                pprint.pprint(data, width=1840)
                exit()

            if data['handle'] not in submitted_handles:
                geometry = models.Geometry(**data)
                geometries.append(geometry)
                submitted_handles.add(data['handle'])
            else:
                n_duplicates += 1
                duplicates.append(data['handle'])



            if i % options.N == 0:
                bulk_upsert(models, geometries)
                geometries = []
                print(repository_name, i, '{0:.4f} s'.format((time.time() - time0) / options.N))
                if n_duplicates > 0:
                    print('Duplicates: {n_duplicates}'.format(n_duplicates=n_duplicates))
                time0 = time.time()

    bulk_upsert(models, geometries)

    if n_duplicates > 0:
        print('Duplicates: {n_duplicates}'.format(n_duplicates=n_duplicates))
        pprint.pprint(duplicates)


    print("Number of errors {n_errors}".format(**locals()))
    print("Erroneous lines")
    for j, line in zip(error_lines_nr, error_lines):
        print(j, line)

if __name__ == '__main__':

    import optparse
    parser = optparse.OptionParser()
    parser.add_option('-t', '--test', dest='test', default=False, action='store_true')
    parser.add_option('-N', '--entries-per-batch', type=int, dest='N', default=500)
    options, args = parser.parse_args()
    print(args)
    print(len(args))
    if len(args) < 1:
        raise UserWarning("Usage: ./ingest <filename1> [<filename2> ...]")
    for filename in args:
        main(filename=filename, options=options)
