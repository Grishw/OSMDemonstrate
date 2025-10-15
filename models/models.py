from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, Text
from geoalchemy2 import Geometry

Base = declarative_base()

class Way(Base):
    __tablename__ = "ways"   
    id = Column(Integer, primary_key=True)
    tags = Column(Text)  
    linestring = Column(Geometry('LINESTRING', srid=4326))

class Node(Base):
    __tablename__ = "nodes"
    id = Column(Integer, primary_key=True)
    tags = Column(Text)
    geom = Column(Geometry('POINT', srid=4326))