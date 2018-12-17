from flask import Flask, render_template, request, redirect
from flask import jsonify, url_for, flash, make_response
from flask import session as login_session
from sqlalchemy import create_engine, asc, func
from sqlalchemy.orm import sessionmaker, joinedload, lazyload
from sqlalchemy.orm import subqueryload, contains_eager
from database_setup import Base, Category, Item, User
import random
import string
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
import httplib2
import json
import requests

app = Flask(__name__)
CLIENT_ID = json.loads(open('client_secrets.json', 'r').
                       read())['web']['client_id']
APPLICATION_NAME = "Udacity Catalog Project"


# Connect to DB & create db session:
engine = create_engine('sqlite:///catalogProj.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)
session = DBSession()


# Authentication functions:

@app.route('/login')
def showLogin():
    state = ''.join(random.choice(string.ascii_uppercase + string.digits)
                    for x in xrange(32))
    login_session['state'] = state
    # login.html - specify state
    return render_template('login.html', STATE=state)


@app.route('/gconnect', methods=['POST'])
def gconnect():
    # validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    # obtain authorization code
    code = request.data

    try:
        # Update auth code into a credential object:
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except:
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that access token is valid:
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s'
           % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])

    # if there was an error in token info, abort:
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # verify the access token is used for intended user:
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
            json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # verify the access token is valid for this app:
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID doesn't match app ID "), 401)
        print "Token's client ID doesn't match app iD"
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps(
                                 'Current user is already connected'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session:
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)

    data = answer.json()

    login_session['username'] = data['name']
    login_session['picture'] = data['picture']
    login_session['email'] = data['email']
    login_session['provider'] = 'google'

    # see if user exists, make new one if not:
    user_id = getUserID(data['email'])

    if not user_id:
        user_id = createUser(login_session)
    login_session['user_id'] = user_id

    output = ''
    output += '<h1>Welcome, '
    output += '<img src="'
    output += login_session['picture']
    output += '" class="userPic">'
    flash("you are now logged in as %s" % login_session['username'])
    return output


@app.route('/gdisconnect')
def gdisconnect():
    # only disconnect if user connected:
    access_token = login_session.get('access_token')
    if access_token is None:
        response = make_response(
            json.dumps('Current user not connected.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response
    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % access_token
    h = httplib2.Http()
    result = h.request(url, 'GET')[0]
    if result['status'] == '200':
        response = make_response(json.dumps('Successfully disconnected'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    else:
        response = make_response(json.dumps(
                                 'Failed to revoke token for given user', 400))
        response.headers['Content-Type'] = 'application/json'
        return response


@app.route('/disconnect')
def disconnect():
    if 'provider' in login_session:
        gdisconnect()
        del login_session['gplus_id']
        del login_session['access_token']
        del login_session['username']
        del login_session['email']
        del login_session['picture']
        del login_session['user_id']
        del login_session['provider']
        flash("You have successfully been logged out.")
        return redirect(url_for('showLatestItems'))
    else:
        flash("You were not logged in.")
        return redirect(url_for('showLatestItems'))


# User functions:

def createUser(login_session):
    newUser = User(name=login_session['username'],
                   email=login_session['email'],
                   picture=login_session['picture'])
    session.add(newUser)
    session.commit()
    user = session.query(User).filter_by(email=login_session['email']).one()
    return user.id


def getUserInfo(user_id):
    user = session.query(User).filter_by(id=user_id).one()
    return user.id


def getUserID(email):
    try:
        user = session.query(User).filter_by(email=email).one()
        return user.id
    except:
        return None


# Helper functions:

# get the first category_id of the query filtered by supplied category_name
# return 0 if query fails or if no category_id found
def getCategoryID(category_name):
    try:
        # due to sqlalchemy version causing errors when user types -
        # existing category with capitalized letters, use ilike() -
        # https://stackoverflow.com/questions/16573095
        # /case-insensitive-flask-sqlalchemy-query
        category_id = session.query(Category).filter(
            Category.name.ilike(category_name)).first().id
    except:
        category_id = 1
    if not category_id:
        category_id = 1
    return category_id


# get the first item_id of the query filtered by supplied itemName
# return 0 if query fails or if no item_id found
def getItemID(itemName):
    try:
        # due to sqlalchemy version causing errors when user types -
        # existing category with capitalized letters, use ilike() -
        # https://stackoverflow.com/questions/16573095
        # /case-insensitive-flask-sqlalchemy-query
        item_id = session.query(Item).filter(Item.name.ilike(
                                             itemName)).first().id
    except:
        item_id = 1
    if not item_id:
        item_id = 1
    return item_id


# Catalog Functions:

# Default route and main route:
@app.route('/')
@app.route('/catalog')
def showLatestItems():
    categories = session.query(Category).order_by(Category.name)
    items = session.query(Item).order_by(asc(Item.name)).limit(3)
    if 'username' not in login_session:
        return render_template('public_catalog.html',
                               categories=categories, items=items)
    else:
        return render_template('catalog.html',
                               categories=categories, items=items)


# show category:
@app.route('/catalog/<category_name>')
@app.route('/catalog/<category_name>/items')
def showCategory(category_name):
    category_id = request.args.get('category_id')
    categories = session.query(Category).order_by(Category.name)
    # if id is not passed, get the id of the first result of
    # the category query filtered by supplied name in url:
    if not category_id:
        category_id = getCategoryID(category_name)
        # set category_name according to category_id:
        category_name = session.query(
            Category).filter_by(id=category_id).one().name

    items = session.query(
        Item).filter_by(category_id=category_id).order_by(
        asc(Item.name)).limit(3)
    # if user isn't logged in render public page, else, render category page:
    if 'username' not in login_session:
        return render_template('public_category.html',
                               categories=categories,
                               items=items,
                               category_name=category_name)
    else:
        return render_template('category.html',
                               categories=categories, items=items,
                               category_name=category_name,
                               category_id=category_id)


# show item:
@app.route('/catalog/<category_name>/<itemName>')
def showItem(category_name, itemName):
    categories = session.query(Category).order_by(Category.name)
    item_id = request.args.get('item_id')
    # if id is not passed, get the id of the first result of
    # the category query filtered by supplied name in url:
    if not item_id:
        item_id = getItemID(itemName)

    item = session.query(Item).filter_by(id=item_id).one()
    # if user isn't logged in render public page, else, render item page:
    if 'username' not in login_session:
        return render_template('public_item.html', categories=categories,
                               category_name=category_name, item=item)
    else:
        return render_template('item.html', categories=categories,
                               category_name=category_name, item=item)


# new category:
@app.route('/newCategory', methods=['GET', 'POST'])
def newCategory():
    categories = session.query(Category).order_by(Category.name)
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'POST':
        newCategory = Category(
            name=request.form['name'], user_id=login_session['user_id'])
        session.add(newCategory)
        flash('New category created: %s' % newCategory.name)
        session.commit()
        return redirect('/')
    else:
        return render_template('newCategory.html', categories=categories)


# new item:
@app.route('/newItem', methods=['GET', 'POST'])
def newItem():
    categories = session.query(Category).order_by(Category.name)
    if 'username' not in login_session:
        return redirect('/login')
    if request.method == 'POST':
        newItem = Item(
            name=request.form['name'],
            category_id=request.form['category_id'],
            description=request.form['description'],
            user_id=login_session['user_id'])
        session.add(newItem)
        flash('New item created: %s' % newItem.name)
        session.commit()
        return redirect('/')
    else:
        return render_template('newItem.html', categories=categories)


# edit category:
@app.route('/catalog/<category_id>/edit', methods=['GET', 'POST'])
def editCategory(category_id):
    if 'username' not in login_session:
        return redirect('/login')
    categories = session.query(Category).order_by(Category.name)
    if not category_id:
        flash('No category found')
        return redirect('/')
    category = session.query(Category).filter_by(id=category_id).one()
    if category.user_id != login_session['user_id']:
        flash('You are not authorized to edit this category')
        return redirect('/')
    if request.method == 'POST':
        category.name = request.form['name']
        session.commit()
        flash('Category edited')
        return redirect('/')
    else:
        return render_template('editCategory.html',
                               categories=categories, category=category)


# edit item:
@app.route('/catalog/<category_name>/<item_id>/edit', methods=['GET', 'POST'])
def editItem(category_name, item_id):
    if 'username' not in login_session:
        return redirect('/login')
    categories = session.query(Category).order_by(Category.name)
    item = session.query(Item).filter_by(id=item_id).one()
    if not item:
        flash('no item found')
        return redirect('/')
    if item.user_id != login_session['user_id']:
        flash('You are not authorized to edit this item')
        return redirect('/')
    if request.method == 'POST':
        item.name = request.form['name']
        item.description = request.form['description']
        item.category_id = request.form['category_id']
        session.commit()
        flash('Item edited')
        return redirect('/')
    else:
        return render_template('editItem.html', categories=categories,
                               category_name=category_name, item=item)


# delete category:
@app.route('/catalog/<category_id>/delete', methods=['GET', 'POST'])
def deleteCategory(category_id):
    if 'username' not in login_session:
        return redirect('/login')
    categories = session.query(Category).order_by(Category.name)
    if not category_id:
        flash('No category found')
        return redirect('/')
    category = session.query(Category).filter_by(id=category_id).one()
    if category.user_id != login_session['user_id']:
        flash('You are not authorized to delete this category')
        return redirect('/')
    if request.method == 'POST':
        if request.form['submit'] == 'cancel':
            return redirect('/')
        session.delete(category)
        session.commit()
        flash('Category deleted')
        return redirect('/')
    else:
        return render_template('deleteCategory.html',
                               categories=categories, category=category)


# delete item:
@app.route('/catalog/<category_name>/<item_id>/delete',
           methods=['GET', 'POST'])
def deleteItem(category_name, item_id):
    if 'username' not in login_session:
        return redirect('/login')
    categories = session.query(Category).order_by(Category.name)
    if not item_id:
        flash('No item found')
        return redirect('/')
    item = session.query(Item).filter_by(id=item_id).one()
    if item.user_id != login_session['user_id']:
        flash('You are not authorized to delete this item')
        return redirect('/')
    if request.method == 'POST':
        if request.form['submit'] == 'cancel':
            return redirect('/')
        session.delete(item)
        session.commit()
        flash('Item deleted')
        return redirect('/')
    else:
        return render_template('deleteItem.html',
                               categories=categories, item=item)


# JSON:
@app.route('/catalog.json')
def showCatalogJSON():
    categories = session.query(Category).all()
    return jsonify(category=[i.serialize for i in categories])


if __name__ == '__main__':
    app.secret_key = 'Reach for the sky and get skittles'
    # app.debug = True
    app.run(host='0.0.0.0', port=8000)
