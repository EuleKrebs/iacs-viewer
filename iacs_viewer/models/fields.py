from iacs_viewer.database import db
from geoalchemy2 import Geometry

class Fields(db.Model):
    __tablename__ = 'fields'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    
    field_id = db.Column(db.String, nullable=False)
    farm_id = db.Column(db.String, nullable=True)

    crop_code = db.Column(db.String, nullable=True)
    crop_name = db.Column(db.String, nullable=True)
    EC_trans_n = db.Column(db.String, nullable=True)
    EC_hcat_n = db.Column(db.String, nullable=True)
    EC_hcat_c = db.Column(db.String, nullable=True)

    organic = db.Column(db.Boolean, nullable=True)
    field_size = db.Column(db.Float, nullable=True)
    crop_area = db.Column(db.Float, nullable=True)

    nation = db.Column(db.String, nullable=True)
    year = db.Column(db.Integer, nullable=True)

    geometry = db.Column(Geometry("POLYGON"), nullable=True)

    updated_at = db.Column(db.DateTime, nullable=False, default=db.func.now(), onupdate=db.func.now())

    #__table_args__ = (
    #    db.UniqueConstraint('field_id', 'nation', 'year', name='unique_field_year'),
    #    {'schema': 'iacs'}
    #)

    def __init__(self, field_id, crop_code, crop_name, EC_trans_n, EC_hcat_n, EC_hcat_c,
                 field_size, nation, year, farm_id=None, organic=None,
                 crop_area=None, geometry=None, **kwargs):

        self.field_id = field_id
        self.farm_id = farm_id

        self.crop_code = crop_code
        self.crop_name = crop_name
        self.EC_trans_n = EC_trans_n
        self.EC_hcat_n = EC_hcat_n
        self.EC_hcat_c = EC_hcat_c

        self.organic = organic
        self.field_size = field_size
        self.crop_area = crop_area

        self.nation = nation
        self.year = year
        self.geometry = geometry

        for key, value in kwargs.items():
            setattr(self, key, value)

    def register_if_not_exist(self):
        exists = Fields.query.filter_by(field_id=self.field_id, nation=self.nation, year=self.year).first()
        if not exists:
            db.session.add(self)
            db.session.commit()
            return True
        return False

    @staticmethod
    def get_by_field_id(field_id, nation, year):
        return Fields.query.filter_by(field_id=field_id, nation=nation, year=year).first()

    def __repr__(self):
        return f"<Fields {self.field_id} ({self.year}) – {self.crop_name}>"