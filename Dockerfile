FROM lambci/lambda:build-python3.7
LABEL maintainer="<sysadmin@datamermaid.org>"

WORKDIR /var/task
# Fancy prompt to remind you you are in zappashell
RUN echo 'export PS1="\[\e[36m\]zappashell>\[\e[m\] "' >> /root/.bashrc

# Create and activate venv for shell
RUN python -m venv /var/ve
RUN echo 'source /var/ve/bin/activate' >> /root/.bashrc

COPY ./src/requirements.txt /var/task/requirements.txt
# https://github.com/jkehler/awslambda-psycopg2 -- but zappa will do this for us
#RUN mkdir /var/ve/lib/python3.6/site-packages/psycopg2
#COPY psycopg2-3.6/* /var/ve/lib/python3.6/site-packages/psycopg2/
RUN /bin/bash -c "source /var/ve/bin/activate && pip install -r /var/task/requirements.txt"

CMD ["tail", "-f", "/dev/null"]
