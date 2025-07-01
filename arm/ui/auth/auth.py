"""
ARM route blueprint for auth pages
Covers
- user_loader [GET, POST]
- unauthorized_handler [GET]
- login [GET, POST]
- logout [GET]
- update_password [GET, POST]
"""
from sqlite3 import OperationalError
import bcrypt
from flask import redirect, render_template, request, Blueprint, flash, app, session
from flask_login import LoginManager, login_required, \
    current_user, login_user, logout_user  # noqa: F401

from arm.ui import app, db, constants   # noqa: F811
from arm.models.user import User
from arm.ui.forms import SetupForm, DBUpdate, PasswordReset
import arm.ui.utils as ui_utils

route_auth = Blueprint('route_auth', __name__,
                       template_folder='templates',
                       static_folder='../static')

# Define the Flask login manager
login_manager = LoginManager()
login_manager.init_app(app)


@route_auth.route('/login', methods=['GET', 'POST'])
def login():
    """
    Login page if login is enabled
    :return: redirect
    """
    page_support_databaseupdate = "support/databaseupdate.html"

    # Check the database is current
    db_update = ui_utils.arm_db_check()
    if not db_update["db_current"] or not db_update["db_exists"]:
        dbform = DBUpdate(request.form)
        return render_template(page_support_databaseupdate, db_update=db_update, dbform=dbform)

    return_redirect = None
    # if there is no user in the database
    try:
        user_list = User.query.all()
        # If we don't raise an exception but the usr table is empty
        if not user_list:
            app.logger.error("No admin found")
    except OperationalError as e:
        # Handle no data found when querying the db
        flash(constants.NO_ADMIN_ACCOUNT, "danger")
        app.logger.error(constants.NO_ADMIN_ACCOUNT)
        app.logger.error(f"ERROR: Missing Data in the ARM User Table: {e}")
        dbform = DBUpdate(request.form)
        db_update = ui_utils.arm_db_check()
        return render_template(page_support_databaseupdate, db_update=db_update, dbform=dbform)

    # if a user is logged in
    if current_user.is_authenticated:
        return_redirect = redirect(constants.HOME_PAGE)

    form = SetupForm()
    if form.validate_on_submit():
        login_username = form.username.data.strip()
        login_password = form.password.data.strip().encode('utf-8')
        # we know there is only ever 1 admin account, so we can pull it and check against it locally
        admin = User.query.filter_by().first()
        app.logger.debug("user= " + str(admin))
        # our pass
        password = admin.password
        # hashed pass the user provided
        login_hashed = bcrypt.hashpw(login_password, admin.hash)

        if login_hashed == password and login_username == admin.email:
            login_user(admin)
            app.logger.debug("user was logged in - redirecting")
            return_redirect = redirect(constants.HOME_PAGE)
        else:
            flash("Something isn't right", "danger")

    # If nothing has gone wrong, give them the login page
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
    updating the password for the admin account
    """
    # get current user
    user = User.query.first()
    session["page_title"] = "Update Admin Password"

    # After a login for is submitted
    form = PasswordReset()

    if form.validate_on_submit():
        # Get form values
        username = form.username.data.strip()
        new_password = form.new_password.data.strip().encode('utf-8')
        old_password = form.old_password.data.strip().encode('utf-8')

        # Get current password and dehash
        user = User.query.filter_by(email=username).first()
        current_password = user.password
        hashed = user.hash
        login_hashed = bcrypt.hashpw(old_password, hashed)

        # If user entered correct password
        if login_hashed == current_password:
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
                app.logger.error(f"Error in updating password: {error}")
        else:
            flash("Current password does not match", "danger")
            app.logger.error("Current password does not match")

    return render_template('update_password.html', user=user.email, form=form)


@login_manager.user_loader
def load_user(user_id):
    """
    Logged in check
    :param user_id:
    :return:
    """
    try:
        return User.query.get(int(user_id))
    except OperationalError as e:
        app.logger.error("Error getting user")
        app.logger.error(f"ERROR: {e}")
        return None


@login_manager.unauthorized_handler
def unauthorized():
    """
    User isn't authorised to view the requested page
    :return: redirect to login page
    """
    return redirect('/login')
