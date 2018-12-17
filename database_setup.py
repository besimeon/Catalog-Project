from sqlalchemy import Column, create_engine, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref


Base = declarative_base()


class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    name = Column(String(80), nullable=False)
    email = Column(String(80), nullable=False)
    picture = Column(String(250))


class Category(Base):
    __tablename__ = 'category'

    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship(User)
    # per http://docs.sqlalchemy.org/en/latest/
    # orm/basic_relationships.html
    # specify relationship in parent (eg, this class)
    # and specify back_populates parameter:
    items = relationship("Item", back_populates="category")

    @property
    def serialize(self):
        """ Return object data in serializable format:"""
        return {
            'id': self.id,
            'name': self.name,
            # call method which returns object's relations in
            # serializable format:
            'items': self.serialize_items,
        }

    # Per reply by user 'plaes' in the following thread:
    # http://archive.is/HKSvJ , creating a method to serialize
    # an object's relations:
    @property
    def serialize_items(self):
        return [item.serialize for item in self.items]


class Item(Base):
    __tablename__ = 'item'

    id = Column(Integer, primary_key=True)
    name = Column(String(80), nullable=False)
    description = Column(String(250))
    category_id = Column(Integer, ForeignKey('category.id'))
    # per http://docs.sqlalchemy.org/en/latest/
    # orm/basic_relationships.html
    # specify back_populates parameter:
    category = relationship(Category, back_populates="items")
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship(User)

    @property
    def serialize(self):
        """ Return object data in serializable format:"""
        return{
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'category_id': self.category_id,
        }


engine = create_engine('sqlite:///catalogProj.db')


Base.metadata.create_all(engine)
