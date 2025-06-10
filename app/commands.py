# app/commands.py
import click
from flask.cli import with_appcontext
from app.extensions import db
from app.models import Role

@click.group()
def db_cli():
    """Database related commands."""
    pass

@click.command('create-roles')
@with_appcontext
def create_roles_command():
    """Creates default roles (admin, user, poster) if they don't exist."""
    click.echo("Checking and creating default roles...")
    try:
        if not Role.query.filter_by(name='admin').first():
            admin_role = Role(name='admin')
            db.session.add(admin_role)
            click.echo("  - Added 'admin' role.")
        if not Role.query.filter_by(name='user').first(): # 'user' role
            user_role = Role(name='user')
            db.session.add(user_role)
            click.echo("  - Added 'user' role.")
        if not Role.query.filter_by(name='poster').first(): # 'poster' role
            poster_role = Role(name='poster')
            db.session.add(poster_role)
            click.echo("  - Added 'poster' role.")
        
        db.session.commit()
        click.echo("Roles creation process complete.")
    except Exception as e:
        db.session.rollback()
        click.echo(f"ERROR: Failed to create roles: {e}", err=True)
        click.echo("Database transaction rolled back.", err=True)