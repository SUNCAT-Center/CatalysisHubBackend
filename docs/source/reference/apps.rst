Apps
=====

HTTP Request to the Apps backend can be made in Python using e.g.
the `requests` library, like so::

    #!/usr/bin/env python

    import requests

    r = requests.get('http://api.catalysis-hub.org/apps/activityMaps/systems/',
            data={
                "activityMap": "OER",
                }
            )
    print(r.content)


Please refer to the following API documentation for details.


AtoMl
-----
.. automodule:: apps.AtoML
    :members:
    :undoc-members:
    :show-inheritance:

.. automodule:: apps.AtoML.run_atoml
    :members:
    :undoc-members:
    :show-inheritance:

Bulk Enumerator
---------------
.. automodule:: apps.bulkEnumerator
    :members:
    :undoc-members:
    :show-inheritance:

CatKitDemo
----------
.. automodule:: apps.catKitDemo
    :members:
    :undoc-members:
    :show-inheritance:

Pourbaix diagrams
-----------------
       
.. automodule:: apps.pourbaix.run_pourbaix
    :members:
    :undoc-members:
    :show-inheritance:

Prototype Search
-----------------

.. automodule:: apps.prototypeSearch
    :members:
    :undoc-members:
    :show-inheritance:

Utilities
---------
.. automodule:: apps.utils
    :members:
    :undoc-members:
    :show-inheritance:
