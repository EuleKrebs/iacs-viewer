from iacs_viewer.database import db

class Resources(db.Model):
    __tablename__ = 'resources'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(255), nullable=False)
    url = db.Column(db.String(255), nullable=False)

    updated_at = db.Column(db.DateTime, nullable=False, default=db.func.now(), onupdate=db.func.now())

    __table_args__ = (
        db.UniqueConstraint('name', 'url', name='uq_resources_name_url'),
        {'schema': 'iacs'}
    )

    def __init__(self, name, url, **kwargs):
        self.name = name
        self.url = url
        for key, value in kwargs.items():
            setattr(self, key, value)

    def register_if_not_exist(self):
        exists = Resources.query.filter_by(name=self.name, url=self.url).first()
        if not exists:
            db.session.add(self)
            db.session.commit()
            return True
        return False

    @staticmethod
    def get_by_name_url(name, url):
        return Resources.query.filter_by(name=name, url=url).first()

    def __repr__(self):
        return f"<Resource(name={self.name}, url={self.url})>"