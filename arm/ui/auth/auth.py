"""
ARM route blueprint for auth pages
Covers
- user_loader [..]
- unauthorized_handler [GET]
- login [GET, POST]
- logout [GET]
- update_password [GET, POST]
"""

import bcrypt
from flask import redirect, render_template, request, Blueprint, flash, app
from flask_login import LoginManager, login_required, \
    current_user, login_user, logout_user  # noqa: F401

from arm.ui import app, db, constants   # noqa: F811
from arm.models import models as models
from arm.ui.forms import SetupForm, DBUpdate
import arm.ui.utils as ui_utils

route_auth = Blueprint('route_auth', __name__,
                       template_folder='templates',
                       static_folder='../static')

# Define the Flask login manager
login_manager = LoginManager()
login_manager.init_app(app)

# Page definitions
page_support_databaseupdate = "support/databaseupdate.html"
redirect_settings = "/settings"


@route_auth.route('/login', methods=['GET', 'POST'])
def login():
    """
    Login page if login is enabled
    :return: redirect
    """
    global page_support_databaseupdate

    # Check the database is current
    db_update = ui_utils.arm_db_check()
    if not db_update["db_current"] or not db_update["db_exists"]:
        dbform = DBUpdate(request.form)
        return render_template(page_support_databaseupdate, db_update=db_update, dbform=dbform)

    return_redirect = None
    # if there is no user in the database
    try:
        user_list = models.User.query.all()
        # If we don't raise an exception but the usr table is empty
        if not user_list:
            app.logger.debug("No admin found")
    except Exception:
        flash(constants.NO_ADMIN_ACCOUNT, "danger")
        app.logger.debug(constants.NO_ADMIN_ACCOUNT)
        dbform = DBUpdate(request.form)
        db_update = ui_utils.arm_db_check()
        return render_template(page_support_databaseupdate, db_update=db_update, dbform=dbform)

    # if user is logged in
    if current_user.is_authenticated:
        return_redirect = redirect(constants.HOME_PAGE)

    form = SetupForm()
    if request.method == 'POST' and form.validate_on_submit():
        login_username = request.form['username']
        # we know there is only ever 1 admin account, so we can pull it and check against it locally
        admin = models.User.query.filter_by().first()
        app.logger.debug("user= " + str(admin))
        # our pass
        password = admin.password
        # hashed pass the user provided
        login_hashed = bcrypt.hashpw(str(request.form['password']).strip().encode('utf-8'), admin.hash)

        if login_hashed == password and login_username == admin.email:
            login_user(admin)
            app.logger.debug("user was logged in - redirecting")
            return_redirect = redirect(constants.HOME_PAGE)
        else:
            flash("Something isn't right", "danger")

    # If nothing has gone wrong give them the login page
    if request.method == 'GET' or return_redirect is None:
        return_redirect = render_template('login.html', form=form)

    return return_redirect


@route_auth.route("/logout")
def logout():
    """
    Log user out
    :return:
    """
    logout_user()
    flash("logged out", "success")
    return redirect('/')


@route_auth.route('/update_password', methods=['GET', 'POST'])
@login_required
def update_password():
    """
    updating password for the admin account
    """
    # get current user
    user = models.User.query.first()

    # After a login for is submitted
    form = SetupForm()
    if request.method == 'POST' and form.validate_on_submit():
        username = str(request.form['username']).strip()
        new_password = str(request.form['newpassword']).strip().encode('utf-8')
        user = models.User.query.filter_by(email=username).first()
        password = user.password
        hashed = user.hash
        # our new one
        login_hashed = bcrypt.hashpw(str(request.form['password']).strip().encode('utf-8'), hashed)
        if login_hashed == password:
            hashed_password = bcrypt.hashpw(new_password, hashed)
            user.password = hashed_password
            user.hash = hashed
            try:
                db.session.commit()
                flash("Password successfully updated", "success")
                app.logger.info("Password successfully updated")
                return redirect("logout")
            except Exception as error:
                flash(str(error), "danger")
                app.logger.debug(f"Error in updating password: {error}")
        else:
            flash("Password couldn't be updated. Problem with old password", "danger")
            app.logger.info("Password not updated, issue with old password")

    return render_template('update_password.html', user=user.email, form=form)


@login_manager.user_loader
def load_user(user_id):
    """
    Logged in check
    :param user_id:
    :return:
    """
    try:
        return models.User.query.get(int(user_id))
    except Exception:
        app.logger.debug("Error getting user")
        return None


@login_manager.unauthorized_handler
def unauthorized():
    """
    User isn't authorised to view the page
    :return: Page redirect
    """
    return redirect('/login')
