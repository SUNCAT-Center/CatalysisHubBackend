pg_dump -n newase -O --host=catalysishub.c8gwuc8jwb7l.us-west-2.rds.amazonaws.com --port=5432 --username=aseroot --dbname=catalysishub --password > pg_dump

psql -c 'drop database travis_ci_test;'
psql -c 'create database travis_ci_test;'
psql travis_ci_test < pg_dump

rm pg_dump

#psql travis_ci_test -c "alter role kirstenwinther set search_path to newase;"

psql travis_ci_test -c "DELETE FROM publication WHERE pub_id in ('MamunBinary2018', 'RolingConfigurational2017', 'BoesAdsorption2018');"

psql travis_ci_test -c "DELETE FROM keys WHERE id in (select distinct id from systems where unique_id not in (select distinct ase_id from reaction_system));"

psql travis_ci_test -c "DELETE FROM species WHERE id in (select distinct id from systems where unique_id not in (select distinct ase_id from reaction_system));"
psql travis_ci_test -c "DELETE FROM text_key_values WHERE id in (select distinct id from systems where unique_id not in (select distinct ase_id from reaction_system));"
psql travis_ci_test -c "DELETE FROM number_key_values WHERE id in (select distinct id from systems where unique_id not in (select distinct ase_id from reaction_system));"

#psql travis_ci_test -c "DELETE FROM systems WHERE unique_id not in (select distinct ase_id from reaction_system);"

python delete_lost_systems.py

#psql travis_ci_test -c "DROP schema public;"
#psql travis_ci_test -c "ALTER schema newase rename to public;"

pg_dump -n public -O travis_ci_test > pg_dump
