from flask import Blueprint, render_template

main = Blueprint('main', __name__)


@main.route("/")
def index():
    return render_template("index.html")


@main.route("/api/docs")
def api_docs():
    return render_template("swagger.html")
