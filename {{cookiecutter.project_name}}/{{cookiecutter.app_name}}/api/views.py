from flask import Blueprint, current_app, jsonify
from flask_restful import Api
from marshmallow import ValidationError
from {{cookiecutter.app_name}}.extensions import apispec
from {{cookiecutter.app_name}}.api.resources import UserResource, UserList
from {{cookiecutter.app_name}}.api.schemas import UserSchema

from threading import Lock # Workaround

blueprint = Blueprint("api", __name__, url_prefix="/api/v1")
api = Api(blueprint)


api.add_resource(UserResource, "/users/<int:user_id>", endpoint="user_by_id")
api.add_resource(UserList, "/users", endpoint="users")


blueprint._before_request_lock = Lock()
blueprint._got_first_request = False


# Workaround
# @blueprint.before_app_first_request
@blueprint.before_request
def register_views():
    if blueprint._got_first_request:
        return
    with blueprint._before_request_lock:
        if blueprint._got_first_request:
            return
        blueprint._got_first_request = True
# end Workaround

    apispec.spec.components.schema("UserSchema", schema=UserSchema)
    apispec.spec.path(view=UserResource, app=current_app)
    apispec.spec.path(view=UserList, app=current_app)


@blueprint.errorhandler(ValidationError)
def handle_marshmallow_error(e):
    """Return json error for marshmallow validation errors.

    This will avoid having to try/catch ValidationErrors in all endpoints, returning
    correct JSON response with associated HTTP 400 Status (https://tools.ietf.org/html/rfc7231#section-6.5.1)
    """
    return jsonify(e.messages), 400
