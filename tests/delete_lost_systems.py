import psycopg2


con = psycopg2.connect(database='travis_ci_test')
        
cur=con.cursor()

cur.execute("(select distinct id from systems where unique_id not in (select distinct ase_id from reaction_system));")

result = cur.fetchall()

for i, id in enumerate(result):
    id = id[0]
    cur.execute("delete from systems where id = {};".format(id))
    print i
    con.commit()
con.close()

    


