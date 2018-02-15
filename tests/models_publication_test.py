ROOT_URL = 'http://localhost:3000'

def app_root_route():
    import app
    import requests
    #with app.app.run() as server:
        #requests.get('{ROOT_URL}/')

def publication_has_pub_id_test():
    import models
    publication = models.Publication()
    if not hasattr(publication, 'pub_id'):
        raise TypeError('publication has no attribute pub_id')


def publication_has_authors_test():
    import models
    publication = models.Publication()
    if not hasattr(publication, 'authors'):
        raise TypeError('publication has no attribute authors')


def publication_has_title_test():
    import models
    publication = models.Publication()
    if not hasattr(publication, 'title'):
        raise TypeError('publication has no attribute title')


def publication_has_journal_test():
    import models
    publication = models.Publication()
    if not hasattr(publication, 'journal'):
        raise TypeError('publication has no attribute journal')


def publication_has_number_test():
    import models
    publication = models.Publication()
    if not hasattr(publication, 'number'):
        raise TypeError('publication has no attribute number')


def publication_has_pages_test():
    import models
    publication = models.Publication()
    if not hasattr(publication, 'pages'):
        raise TypeError('publication has no attribute pages')


def publication_has_year_test():
    import models
    publication = models.Publication()
    if not hasattr(publication, 'year'):
        raise TypeError('publication has no attribute year')


def publication_has_publisher_test():
    import models
    publication = models.Publication()
    if not hasattr(publication, 'publisher'):
        raise TypeError('publication has no attribute publisher')


def publication_has_doi_test():
    import models
    publication = models.Publication()
    if not hasattr(publication, 'doi'):
        raise TypeError('publication has no attribute doi')


def publication_has_tags_test():
    import models
    publication = models.Publication()
    if not hasattr(publication, 'tags'):
        raise TypeError('publication has no attribute tags')


def publication_has_pubtextsearch_test():
    import models
    publication = models.Publication()
    if not hasattr(publication, 'pubtextsearch'):
        raise TypeError('publication has no attribute pubtextsearch')

