#!/usr/bin/env python
import os
import ase.db

db = ase.db.connect(
    'postgresql://catvisitor:' +
    os.environ['DB_PASSWORD'] +
    '@catappdatabase.cjlis1fysyzx.us-west-1.rds.amazonaws.com:5432/catappdatabase')
for i, elem in enumerate(db.select('Cu,Pd')):

    print('\n\n\n--------------')
    for key in elem:
        print('{0:22}: {1}'.format(key, elem[key]))
