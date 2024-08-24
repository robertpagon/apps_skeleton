import os
from flask import Flask, render_template
from {{cookiecutter.app_name}} import api
from {{cookiecutter.app_name}} import auth
from {{cookiecutter.app_name}} import manage
from {{cookiecutter.app_name}}.extensions import apispec
from {{cookiecutter.app_name}}.extensions import db
from {{cookiecutter.app_name}}.extensions import jwt
from {{cookiecutter.app_name}}.extensions import migrate

{%- if cookiecutter.use_celery == "yes"%}, celery{% endif%}

# WEB
from {{cookiecutter.app_name}}.extensions import login_manager
from {{cookiecutter.app_name}}.extensions import bcrypt
from {{cookiecutter.app_name}}.extensions import toolbar
from {{cookiecutter.app_name}}.extensions import bootstrap


def create_app(testing=False):
    """Application factory, used to create application"""
    app = Flask("{{cookiecutter.app_name}}",
        template_folder="client/templates",
        static_folder="client/static",
    )

    # app.config.from_object("{{cookiecutter.app_name}}.config")
    app_settings = os.getenv(
        "APP_SETTINGS", "{{cookiecutter.app_name}}.config.ProductionConfig"
    )
    app.config.from_object(app_settings)

    if testing is True:
        app.config["TESTING"] = True

    configure_extensions(app)
    configure_cli(app)
    configure_apispec(app)
    register_blueprints(app)

    from {{cookiecutter.app_name}}.bus_logic import myapp
    ''' Ovdje se može ...
    '''
    print(f"NAZIV APLIKACIJE JE: {myapp.recognize_source_from_filename('MYAPP_njuskalo_nesto.py')} (Trebalo bi biti MYAPP)")

    # WEB
    # flask login
    from {{cookiecutter.app_name}}.server.models import User

    login_manager.login_view = "user.login"
    login_manager.login_message_category = "danger"

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.filter(User.id == int(user_id)).first()

    # error handlers
    @app.errorhandler(401)
    def unauthorized_page(error):
        return render_template("errors/401.html"), 401

    @app.errorhandler(403)
    def forbidden_page(error):
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def page_not_found(error):
        return render_template("errors/404.html"), 404

    @app.errorhandler(500)
    def server_error_page(error):
        return render_template("errors/500.html"), 500

    # shell context for flask cli
    @app.shell_context_processor
    def ctx():
        return {"app": app, "db": db}

    # end WEB

    return app


def configure_extensions(app):
    """Configure flask extensions"""
    db.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)

    # WEB
    login_manager.init_app(app)
    bcrypt.init_app(app)
    toolbar.init_app(app)
    bootstrap.init_app(app)


def configure_cli(app):
    """Configure Flask 2.0's cli for easy entity management"""
    app.cli.add_command(manage.init)


def configure_apispec(app):
    """Configure APISpec for swagger support"""
    apispec.init_app(app, security=[{"jwt": []}])
    apispec.spec.components.security_scheme(
        "jwt", {"type": "http", "scheme": "bearer", "bearerFormat": "JWT"}
    )
    apispec.spec.components.schema(
        "PaginatedResult",
        {
            "properties": {
                "total": {"type": "integer"},
                "pages": {"type": "integer"},
                "next": {"type": "string"},
                "prev": {"type": "string"},
            }
        },
    )


def register_blueprints(app):
    """Register all blueprints for application"""
    app.register_blueprint(auth.views.blueprint)
    app.register_blueprint(api.views.blueprint)
    
    # WEB
    from {{cookiecutter.app_name}}.server.user.views import user_blueprint
    from {{cookiecutter.app_name}}.server.main.views import main_blueprint

    app.register_blueprint(user_blueprint)
    app.register_blueprint(main_blueprint)

{%- if cookiecutter.use_celery == "yes" %}


def init_celery(app=None):
    app = app or create_app()
    celery.conf.update(app.config.get("CELERY", {}))

    class ContextTask(celery.Task):
        """Make celery tasks work with Flask app context"""

        def __call__(self, *args, **kwargs):
            with app.app_context():
                return self.run(*args, **kwargs)

    celery.Task = ContextTask
    return celery
{%- endif %}
