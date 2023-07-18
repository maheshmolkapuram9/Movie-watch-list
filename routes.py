from flask import Flask,Blueprint,render_template,session,redirect,url_for,request,current_app,flash
from forms import MovieForm,ExtendedMovieForm,RegisterForm,LoginForm
import uuid
from dataclasses import asdict
from models import Movie,Register
import datetime
from passlib.hash import pbkdf2_sha256
import functools


pages = Blueprint("pages", __name__ , template_folder="templates", static_folder="static")

def login_required(route):
    @functools.wraps(route)
    def route_wrapper(*args,**kwargs):
        if session.get("email") is None:
            return redirect(url_for("pages.login"))
        return route(*args,**kwargs)
    return route_wrapper


@pages.route("/register", methods = ["GET","POST"])
def register():
    if session.get("email"):
        return redirect(url_for("pages.index"))
    
    form = RegisterForm()
    if form.validate_on_submit():
        user = Register(
            _id = uuid.uuid4().hex,
            email = form.email.data,
            password = pbkdf2_sha256.hash(form.password.data)
        )
        current_app.db.user.insert_one(asdict(user))
        flash("User registered sucessfully")
        return redirect(url_for("pages.login"))

    return render_template("register.html",form=form)

@pages.route("/login",methods=["GET","POST"])
def login():
    if session.get("email"):
        return redirect(url_for("pages.index"))
    form = LoginForm()
    if form.validate_on_submit():
        user_data = current_app.db.user.find_one({"email":form.email.data})
        if not user_data:
            flash("Invalid Login credentials", category="danger")
            return redirect(url_for("pages.login"))
        user = Register(**user_data)
        if user and pbkdf2_sha256.verify(form.password.data,user.password):
            flash("Sucessfully Logged in")
            session["email"] = user.email
            session["user_id"] = user._id
            return redirect(url_for("pages.index"))
        flash("Invalid Login credentials", category="danger")
    return render_template("login.html", form=form)

@pages.route("/logout")
def logout():
    current_theme = session.get("theme")
    session.clear()
    session["theme"] = current_theme
    return redirect(url_for("pages.login"))

@pages.route("/")
@login_required
def index():
    user_data = current_app.db.user.find_one({"email":session["email"]})
    users = Register(**user_data)
    movie_data = current_app.db.watchlist.find({"_id":{"$in":users.movies}})
    movies = [Movie(**movie) for movie in movie_data]

    return render_template(
        "index.html",
        title="Movies Watchlist",
        movies_data=movies,
    )

@pages.route("/add", methods=["GET", "POST"])
@login_required
def add():
    form = MovieForm()

    if form.validate_on_submit():
        movie = Movie(
            _id = uuid.uuid4().hex,
            title = form.title.data,
            director = form.director.data,
            year = form.year.data
        )
        current_app.db.watchlist.insert_one(asdict(movie))
        current_app.db.user.update_one(
            {"email":session["email"]}, {"$push":{"movies":movie._id}}
            )
        
        return redirect(url_for('pages.movie', _id=movie._id)) 
    return render_template("new_movie.html", form=form)

@pages.route("/movie/edit/<string:_id>", methods=["GET","POST"])
@login_required
def edit_movie(_id: str):
    movie = Movie(**current_app.db.watchlist.find_one({"_id":_id}))
    form = ExtendedMovieForm(obj = movie)
    if form.validate_on_submit():
        print("validated")
        movie.title = form.title.data
        movie.director = form.director.data
        movie.year = form.year.data
        movie.cast = form.cast.data
        movie.series = form.series.data
        movie.tags = form.tags.data
        movie.discription = form.discription.data
        movie.video_link = form.video_link.data 
        current_app.db.watchlist.update_one({"_id": movie._id}, {"$set": asdict(movie)})
        return redirect(url_for('pages.movie',_id=_id))
    return render_template("movie_form.html",movie=movie,form=form)

@pages.get("/movie/<string:_id>")
@login_required
def movie(_id: str):
    movie = Movie(**current_app.db.watchlist.find_one({"_id": _id}))
    return render_template("movie_details.html", movie=movie)

@pages.get("/movie/<string:_id>/rate")
@login_required
def rate_movie(_id):
    rating = int(request.args.get("rating"))
    current_app.db.watchlist.update_one({"_id":_id}, {"$set": {"rating":rating}})
    return redirect(url_for("pages.movie",_id=_id))

@pages.get("/movie/<string:_id>/date")
@login_required
def watch_today(_id):
    current_app.db.watchlist.update_one({"_id":_id},{"$set":{"last_watched":datetime.datetime.today()}})
    return redirect(url_for("pages.movie", _id=_id))

@pages.get("/toggle-theme")
def toggle_theme():
    current_theme = session.get('theme')
    if current_theme == 'dark':
        session["theme"] = 'light'
    else:
        session["theme"] = "dark"
    return redirect(request.args.get("current_page"))

