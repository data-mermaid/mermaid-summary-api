import time
from fabric.api import local


# HELPER FUNCTIONS

def _api_cmd(cmd):
    return 'docker exec -it summary_api_build /bin/bash -c "source /var/ve/bin/activate && {}"'.format(cmd)


# FABRIC COMMANDS

def build():
    local("docker-compose build")


def build_nocache():
    local("docker-compose build --no-cache")


def up():
    local("docker-compose up -d")


def down():
    local("docker-compose down")


def runserver():
    local(_api_cmd("python manage.py runserver 0.0.0.0:8000"))


def makemigrations():
    local(_api_cmd("python manage.py makemigrations summary_api"))


def migrate():
    local(_api_cmd("python manage.py migrate summary_api"))


def refresh_view(viewname=None):
    viewname = viewname or 'vw_summary_site'
    local(_api_cmd("python manage.py refresh_view {}".format(viewname)))


def shell_plus():
    local(_api_cmd("python manage.py shell_plus"))


def shell():
    local("docker exec -it summary_api_build /bin/bash")


def fresh_install():
    down()
    build()
    up()
    migrate()
