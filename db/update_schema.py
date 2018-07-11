#!/usr/bin/python3

import sqlite3
import os
import yaml
import errno

yamlfile = "C:/etc/arm/arm.yaml"
with open(yamlfile, "r") as f:
    cfg = yaml.load(f)

db_file = cfg['DBFILE']
print("Updating ARM database " + db_file)

# if not os.path.exists(db_file):
#     print("No database file exists.  Creating arm.db")
#     with open(db_file, 'w'):
#             pass

if not os.path.exists(os.path.dirname(db_file)):
    try:
        os.makedirs(os.path.dirname(db_file))
    except OSError as exc:  # Guard against race condition
        if exc.errno != errno.EEXIST:
            raise

with open(db_file, "w") as f:
    pass


def create_connection(db_file):
    """ Create a database connection to the SQLite database

    db_file: database file\n
    returns: Connection object or None\n
    """
    try:
        conn = sqlite3.connect(db_file)
        return conn
    except sqlite3.Error as e:
        print(e)

    return None


conn = create_connection(db_file)
c = conn.cursor()

create_version_table = """CREATE TABLE version (
    version varchar(10) NOT NULL
    )"""

update_version = """REPLACE INTO version (version) values ('1.0.0')"""

create_rips_table = """CREATE TABLE IF NOT EXISTS rips (
    rip_id integer PRIMARY KEY AUTOINCREMENT,
    arm_version text,
    crc64 text,
    type text,
    label text,
    title text,
    year integer,
    rip_title_ms text,
    rip_title_omdb text,
    ripmethod text,
    mkv_args text,
    hb_preset_dvd text,
    hb_preset_bd text,
    hb_args_dvd text,
    hb_args_bd text,
    errors text,
    logfile text,
    start_time datetime,
    stop_time datetime,
    rip_time datetime,
    status text
    )"""


def get_db_version():
    c.execute("Select MAX(version) from version")
    return str(c.fetchone()[0])


print("Creating version table")
c.execute(create_version_table)
c.execute(update_version)
print("Complete")
print("Creating rips table")
c.execute(create_rips_table)
print("Complete")
print("**************")
print("Database upgrade complete.  DB version is: " + get_db_version())

# with conn:
#     sql = ''' INSERT INTO rips(crc64, arm_version, type, label, year, start_time) VALUES(?,?,?,?,?,?) '''
#     values = ('8kj389d68', '2.0.0-beta', 'dvd', 'newlabel', '2005', datetime.now())
#     c.execute(sql, values)
#     print(str(c.lastrowid))

#     time.sleep(10)

#     sql = '''UPDATE rips SET stop_time = ?, rip_time = ? where rip_id = ?'''
#     values = (datetime.now(),  c.lastrowid)
#     c.execute(sql, values)
#     print(str(c.lastrowid))


conn.close
