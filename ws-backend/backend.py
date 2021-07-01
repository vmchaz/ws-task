import os
from flask import Flask
from flask_restx import Api, Resource, fields
from werkzeug.middleware.proxy_fix import ProxyFix

from flask_sqlalchemy import SQLAlchemy

import json

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get("DATABASE_URI", 'postgresql+psycopg2://postgres_user:rrs@localhost:5434/tmpdb')
app.wsgi_app = ProxyFix(app.wsgi_app)
api = Api(app, version='1.0', title='TodoMVC API',
    description='A simple TodoMVC API',
)

db = SQLAlchemy(app)

ns = api.namespace('items', description='Items operations')


class Item(db.Model):
    __tablename__ = 'items'
    id = db.Column(db.Integer, primary_key=True, unique=True)
    description = db.Column(db.Text)
    status = db.Column(db.Integer)
    
    
    def __init__(self, id, description="", status=0):
        self.id = id
        self.description = description
        self.email = email
        

    def __repr__(self):
        return '<Item {}>'.format(self.id)


@ns.route('/')
class ItemList(Resource):
    def get(self):
        resp_list = []
        qa = Item.query.all()
        for item_obj in qa:
            descr_dict = json.loads(item_obj.description) if item_obj.description else {}
            r = {"description":descr_dict, "status":item_obj.status, "id":item_obj.id}
            resp_list.append(r)
        return resp_list


@ns.route('/<int:id>')
@ns.response(404, 'Item not found')
@ns.param('id', 'The item identifier')
class ItemResource(Resource):
    def get(self, id):        
        
        item_obj = Item.query.get_or_404(id)

        data = json.loads(item_obj.description) if item_obj.description else {}
        r = {"description": data, "id": id, "status": item_obj.status}        
        return r

if __name__ == '__main__':
    app.run(debug=True)
