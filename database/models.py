from sqlalchemy import Column, Integer, BigInteger, String, DateTime, ForeignKey, create_engine
from sqlalchemy.orm import relationship, declarative_base, sessionmaker
from datetime import datetime

Base = declarative_base()
engine = create_engine("sqlite:////home/user/dev/weatherbot/db.db", echo=True)


class Users(Base):
    __tablename__ = 'Users'
    id = Column(Integer, primary_key=True)
    tg_id = Column(BigInteger, nullable=False)
    city = Column(String)
    connection_date = Column(DateTime, nullable=False, default=datetime.now())
    reports = relationship('WeatherReport', backref='report', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return self.tg_id


class WeatherReport(Base):
    __tablename__ = 'WeatherReports'
    id = Column(Integer, primary_key=True)
    owner = Column(Integer, ForeignKey('Users.id'), nullable=False)
    date = Column(DateTime, nullable=False, default=datetime.now())
    temp = Column(Integer, nullable=False)
    feels_like = Column(Integer, nullable=False)
    wind_speed = Column(Integer, nullable=False)
    pressure_mm = Column(Integer, nullable=False)
    city = Column(String(25), nullable=False)

    def __repr__(self):
        return f'{self.date} - {self.city}'


Base.metadata.create_all(engine)

Session = sessionmaker(bind=engine)
session = Session()
