import sqlalchemy as sq
from sqlalchemy.orm import sessionmaker
from models import Account
from utils import write_event_log


class DbClient():
    def __init__(self, db_type, db_name, host, port, user, password):
        self.db = (f'{db_type}://{user}:{password}'
                   f'@{host}:{port}/{db_name}')
        try:
            self.engine = sq.create_engine(self.db)
        except sq.exc.NoSuchModuleError as error:
            write_event_log(error, 'DbClient.__init__')
            raise error

    def start_session(self):
        try:
            Session = sessionmaker(bind=self.engine)
            return Session()
        except sq.exc.OperationalError as error:
            write_event_log(error, 'DbClient.start_session')
            raise error

    def add_record(self, db_session, model, **kwargs):
        db_session.add(model(**kwargs))
        return db_session

    def get_wb_token(self)->list:
        session = self.start_session()
        response = session.query(
            Account.api_key,
        ).filter(Account.mp_id == 2).limit(1)
        return response[0][0]

    def remove_duplicates(self, table, partition):
        connection = self.engine.connect()
        connection.execute(f"""
            DELETE
            FROM {table}
            WHERE id IN (
                SELECT id
                FROM (
                    SELECT id, 
                    row_number() OVER (
                        PARTITION BY {partition}
                        ORDER BY id DESC
                    )
                    FROM {table}) as query
                WHERE row_number != 1
            );
        """)
