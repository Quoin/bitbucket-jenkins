FROM python:3.5-onbuild

VOLUME /data
ENTRYPOINT ["gunicorn", "-c", "gunicorn_conf.py", "bitbucket_jenkins.server:app"]
