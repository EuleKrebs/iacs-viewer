from flask import Blueprint, render_template, request
from iacs_viewer.models.resources import Resources

main = Blueprint('main', __name__)

@main.route("/", methods=["GET", "POST"])
def index():
    resources = Resources.query.all()
    return render_template("index.html", resources=resources)
