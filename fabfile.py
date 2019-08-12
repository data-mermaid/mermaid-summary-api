from invoke import task, run


# HELPER FUNCTIONS

def _api_cmd(cmd):
    return 'docker exec -it summary_api_build /bin/bash -c "source /var/ve/bin/activate && {}"'.format(cmd)


# FABRIC COMMANDS

@task
def build(c):
    run("docker-compose build", pty=True)


@task
def build_nocache(c):
    run("docker-compose build --no-cache", pty=True)


@task
def up(c):
    run("docker-compose up -d", pty=True)


@task
def down(c):
    run("docker-compose down", pty=True)


@task
def runserver(c):
    run(_api_cmd("python manage.py runserver 0.0.0.0:8000"), pty=True)


@task
def makemigrations(c):
    run(_api_cmd("python manage.py makemigrations summary_api"), pty=True)


@task
def migrate(c):
    run(_api_cmd("python manage.py migrate summary_api"), pty=True)


@task
def refresh_view(c, viewname=None):
    viewname = viewname or 'vw_summary_site'
    run(_api_cmd("python manage.py refresh_view {}".format(viewname)), pty=True)


@task
def shell_plus(c):
    run(_api_cmd("python manage.py shell_plus"), pty=True)


@task
def shell(c):
    run("docker exec -it summary_api_build /bin/bash", pty=True)


@task
def fresh_install(c):
    down(c)
    build(c)
    up(c)
    migrate(c)
