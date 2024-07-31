from .setup import *


class ModelActivity(ModelBase):
    P = P
    __tablename__ = f'{P.package_name}_activity'
    __table_args__ = {'mysql_collate': 'utf8_general_ci'}
    __bind_key__ = P.package_name

    id = db.Column(db.Integer, primary_key=True)
    json = db.Column(db.JSON)
    created_time = db.Column(db.DateTime)

    folderid = db.Column(db.String)
    last_item_time = db.Column(db.DateTime)
    
    def __init__(self, folderid):
        self.folderid = folderid
        self.last_item_time = None
        self.created_time = datetime.now()

        with F.app.app_context():
            db.session.add(self)
            db.session.commit()
    
    def update_item(self, dt):
        if self.last_item_time == None or dt > self.last_item_time:
            self.last_item_time = dt
            self.save()
            return True
        return False

    @classmethod
    def get_by_folderid(cls, folderid):
        try:
            with F.app.app_context():
                return F.db.session.query(cls).filter_by(folderid=folderid).first()
        except Exception as e:
            cls.P.logger.error(f'Exception:{str(e)}')
            cls.P.logger.error(traceback.format_exc())
