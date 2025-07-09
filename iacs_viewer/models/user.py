from best_app.database import db
from sqlalchemy.dialects.postgresql import JSON, GEOMETRY  # Assuming PostGIS if using Postgres

class IacsField(db.Model):
    __tablename__ = 'iacs_fields'

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    
    field_id = db.Column(db.String, nullable=False)
    farm_id = db.Column(db.String, nullable=True)

    crop_code = db.Column(db.String, nullable=False)
    crop_name = db.Column(db.String, nullable=False)
    EC_trans_n = db.Column(db.String, nullable=False)
    EC_hcat_n = db.Column(db.String, nullable=False)
    EC_hcat_c = db.Column(db.String, nullable=False)

    organic = db.Column(db.Boolean, nullable=True)
    field_size = db.Column(db.Float, nullable=False)
    crop_area = db.Column(db.Float, nullable=True)

    nation = db.Column(db.String, nullable=False)
    year = db.Column(db.Integer, nullable=False)

    geometry = db.Column(GEOMETRY("POLYGON"), nullable=True)

    __table_args__ = (
        db.UniqueConstraint('field_id', 'nation', 'year', name='unique_field_year'),
    )

    def __init__(self, field_id, crop_code, crop_name, EC_trans_n, EC_hcat_n, EC_hcat_c,
                 field_size, nation, year, farm_id=None, organic=None,
                 crop_area=None, geometry=None):

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

    def register_if_not_exist(self):
        exists = IacsField.query.filter_by(field_id=self.field_id, nation=self.nation, year=self.year).first()
        if not exists:
            db.session.add(self)
            db.session.commit()
        return True

    @staticmethod
    def get_by_field_id(field_id, nation, year):
        return IacsField.query.filter_by(field_id=field_id, nation=nation, year=year).first()

    def __repr__(self):
        return f"<IacsField {self.field_id} ({self.year}) – {self.crop_name}>"