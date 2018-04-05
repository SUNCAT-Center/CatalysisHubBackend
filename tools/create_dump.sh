pg_dump -n public -O --host=catalysishub.c8gwuc8jwb7l.us-west-2.rds.amazonaws.com --port=5432 --username=catroot --dbname=catalysishub --password > pg_dump

psql -c 'drop database travis_ci_test;'
psql -c 'create database travis_ci_test;'
psql travis_ci_test < pg_dump

rm pg_dump
psql travis_ci_test -c "DELETE FROM publication WHERE pub_id in ('MamunBinary2018', 'RolingConfigurational2017', 'BoesAdsorption2018');"

psql travis_ci_test -c "DELETE FROM keys WHERE id in (select distinct id from systems where unique_id not in (select distinct ase_id from reaction_system));"
psql travis_ci_test -c "DELETE FROM species WHERE id in (select distinct id from systems where unique_id not in (select distinct ase_id from reaction_system));"
psql travis_ci_test -c "DELETE FROM text_key_values WHERE id in (select distinct id from systems where unique_id not in (select distinct ase_id from reaction_system));"
psql travis_ci_test -c "DELETE FROM number_key_values WHERE id in (select distinct id from systems where unique_id not in (select distinct ase_id from reaction_system));"

#psql travis_ci_test -c "DELETE FROM systems WHERE unique_id not in (select distinct ase_id from reaction_system);"

python delete_lost_systems.py

pg_dump -n public -O travis_ci_test > pg_dump
