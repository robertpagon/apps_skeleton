import click
from flask.cli import with_appcontext


@click.command("init")
@with_appcontext
def init():
    """Create a new admin user"""
    from {{cookiecutter.app_name}}.extensions import db
    from {{cookiecutter.app_name}}.models import User

    click.echo("create user")
    user = User(username="{{cookiecutter._admin_user_username}}", email="{{cookiecutter._admin_user_email}}", password="{{cookiecutter._admin_user_password}}", active=True)
    db.session.add(user)
    db.session.commit()
    click.echo("created user admin")
