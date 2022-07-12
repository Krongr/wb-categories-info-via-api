import requests
import sqlalchemy
from db_client import DbClient
from models import Category, CategoryAttributes, AttributeDictionaryValue
from wb_api import WbApi
from utils import write_event_log


# DB settings:
TYPE= 'postgresql'
NAME= ''
HOST= ''
PORT= ''
USER= ''
PASSWORD= ''


def collect_parent_categories(wb:WbApi):
    _parent_categories = []
    """Returns a list of parent categories.
    """
    try:
        response = wb.parent_category_list()
    except requests.exceptions.ConnectionError as error:
        write_event_log(error, 'wb.category_list')
        return _parent_categories

    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as error:
        write_event_log(error, 'collect_categories', response.json())
        return _parent_categories

    try:
        category_dict = response.json()['data']
    except KeyError as error:
        write_event_log(error, 'collect_categories', response.json())
        return _parent_categories

    try:
        assert isinstance(category_dict, dict)
    except AssertionError as error:
        write_event_log(
            f'{type(category_dict)} is not "dict" object',
            'collect_categories',
        )
        return _parent_categories

    for _category in category_dict.values():
        try:
            _parent_categories.append(_category['name'])
        except (KeyError, TypeError) as error:
            write_event_log(error, 'collect_categories')
            continue
        
    return _parent_categories

def record_categories_and_attributes(wb:WbApi, db:DbClient,
                                            parent_category):
    """Creates records of the categories and attributes in the DB.
    """
    db_session = db.start_session()
    # Collect a list of categories with atributes:
    try:
        response = wb.categories_by_parent(parent_category)
    except requests.exceptions.ConnectionError as error:
        write_event_log(error, 'wb.categories_by_parent')
        return

    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as error:
        write_event_log(
            error,
            'record_categories_and_attributes',
            response.json(),
        )
        return

    try:
        _categories_with_attributes = response.json()['data']        
    except KeyError as error:
        write_event_log(
            error,
            'record_categories_and_attributes',
            response.json()
        )
        return

    for _category in _categories_with_attributes:
        # Add category record:
        try:
            db_session = db.add_record(
                db_session=db_session,
                model=Category,
                name=_category['name'],
                mp_id=2,
                cat_id=_category['id'],
            )
        except KeyError as error:
            write_event_log(error, 'record_categories_and_attributes')
            continue

        # Add attribute records:
        try:
            _attributes = _category['addin']
            _nm__attributes = _category['nomenclature']['addin']
        except KeyError as error:
            write_event_log(error, 'record_categories_and_attributes')
            continue

        for _entry in (_attributes + _nm__attributes):
            try:
                db_session = db.add_record(
                    db_session=db_session,
                    model=CategoryAttributes,
                    dictionary_id=_entry.get('dictionary'),
                    chid=_entry['type'],
                    is_collection= (True if _entry.get('dictionary') 
                                    else False),
                    is_required=_entry['required'],
                    name=_entry['type'],
                    type=_entry.get('units'),
                    cat_id=_category['id'],
                    db_i=f"{_category['id']}{_entry['type']}",
                )
            except KeyError as error:
                write_event_log(
                    error,
                    'record_categories_and_attributes',
                    response.json()
                )
    
    try:
        db_session.commit()
    except (
        sqlalchemy.exc.InternalError,
        sqlalchemy.exc.IntegrityError,
        sqlalchemy.exc.ProgrammingError,
        sqlalchemy.exc.DataError,
        sqlalchemy.exc.OperationalError,
    ) as error:
        write_event_log(error, 'categories_and_attributes.commit')

def collect_information_about_dictionaries(wb:WbApi):
    """Returns a dict of dictionaries and the number of values in them.
    """
    try:
        response = wb.dictionaries()
    except requests.exceptions.ConnectionError as error:
        write_event_log(error, 'wb.dictionaries')
        return

    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as error:
        write_event_log(
            error,
            'collect_information_about_dictionaries',
            response.json()
        )
        return

    try:
        dictionaries = response.json()['data']
    except KeyError as error:
        write_event_log(error, 'collect_categories', response.json())
        return

    return dictionaries

def record_dictionary_values(wb:WbApi, db:DbClient, dictionary, amount):
    """Creates records of the dictionary values in the DB.
    """
    try:
        response = wb.dictionary_values(dictionary, amount)
    except requests.exceptions.ConnectionError as error:
        write_event_log(error, 'wb.dictionary_values')
        return

    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError as error:
        write_event_log(
            error,
            'record_dictionary_values',
            'raise_for_status'
        )
        return

    try:
        _dictionary_values = response.json()['data']
    except KeyError as error:
        write_event_log(error, 'record_dictionary_values', response.json())
        return

    for i in range(0, amount, 10000):
        db_session = db.start_session()
        for _value in _dictionary_values[i:i+10000]:
            try:
                db_session = db.add_record(
                    db_session=db_session,
                    model=AttributeDictionaryValue,
                    value=_value['key'],
                    picture=None,
                    info=None,
                    attr_param_id=None,
                    chid=dictionary,
                    db_i=f"{dictionary}{_value['key']}",
                )
            except (KeyError, TypeError) as error:
                write_event_log(
                    error,
                    'record_dictionary_values',
                )
        
        try:
            db_session.commit()
        except (
            sqlalchemy.exc.InternalError,
            sqlalchemy.exc.IntegrityError,
            sqlalchemy.exc.ProgrammingError,
            sqlalchemy.exc.DataError,
            sqlalchemy.exc.OperationalError,
        ) as error:
            write_event_log(error, 'record_dictionary_values.commit')

    #Remove duplicates
    try:
        db.remove_duplicates(AttributeDictionaryValue.__tablename__, 'db_i')
    except (
        sqlalchemy.exc.InternalError,
        sqlalchemy.exc.IntegrityError,
        sqlalchemy.exc.ProgrammingError,
        sqlalchemy.exc.DataError,
        sqlalchemy.exc.OperationalError,
    ) as error:
        write_event_log(
            error,
            'record_dictionary_values db.remove_duplicates',
        )

if __name__ == '__main__':
    db = DbClient(TYPE, NAME, HOST, PORT, USER, PASSWORD)

    try:
        auth_token = db.get_wb_token()
    except (
        sqlalchemy.exc.OperationalError,
        sqlalchemy.exc.InternalError,
        sqlalchemy.exc.ProgrammingError,
    ) as error:
        write_event_log(error, 'DbClient.get_credentials')
        raise error

    wb = WbApi(auth_token)

    # Record all available categories and attributes:
    parent_categories = collect_parent_categories(wb)

    if parent_categories:
        for _category in parent_categories:
            record_categories_and_attributes(wb, db, _category)

    #Remove duplicates
    for _table, _partition in (
        (Category.__tablename__, 'cat_id'),
        (CategoryAttributes.__tablename__, 'db_i'),
    ):
        try:
            db.remove_duplicates(_table, _partition)
        except (
            sqlalchemy.exc.InternalError,
            sqlalchemy.exc.IntegrityError,
            sqlalchemy.exc.ProgrammingError,
            sqlalchemy.exc.DataError,
            sqlalchemy.exc.OperationalError,
        ) as error:
            write_event_log(
                error,
                'add_categories_and_attributes_records db.remove_duplicates',
            )

    # Record all dictionary values:
    dictionaries = collect_information_about_dictionaries(wb)
    if dictionaries:
        for dictionary, amount in dictionaries.items():
            if dictionary in ('/ext', '/tnved', '/wbsizes'):
                continue
            print(dictionary)
            record_dictionary_values(wb, db, dictionary, amount)
