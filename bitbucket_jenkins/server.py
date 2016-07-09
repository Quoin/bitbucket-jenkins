import logging
import os
import re
from pprint import pformat
import shelve

from bottle import hook, post, request, default_app, abort

from .bitbucket import BitBucketClient
from .jenkins import JenkinsClient

logging.basicConfig(level=logging.INFO)


bb_client = BitBucketClient(os.environ['BITBUCKET_USERNAME'],
                            os.environ['BITBUCKET_PASSWORD'])

jenkins_client = JenkinsClient(os.environ['JENKINS_URL'],
                               os.environ.get('JENKINS_USERNAME'),
                               os.environ.get('JENKINS_PASSWORD'))


class PRMetadata():
    shelve_path = '/data/pr_metadata'

    def __init__(self, commit_hash, title=None, link=None, jobs_triggered=None):
        self.title = title
        self.link = link
        self.commit_hash = commit_hash
        self.jobs_triggered = jobs_triggered or []
        self.job_to_build_num = {}

    def save(self):
        with shelve.open(self.shelve_path, flag='c') as pr_metadata:
            pr_metadata[self.commit_hash[:12]] = self

    @classmethod
    def fetch_by_commit_hash(cls, commit_hash):
        with shelve.open(cls.shelve_path) as pr_metadata:
            return pr_metadata.get(commit_hash[:12])


def set_jenkins_build_description(job_name, build_num, link, title):
    logging.info('Setting build description for job %s #%d to "%s"',
                 job_name, build_num, title)
    jenkins_client.set_build_description(
        job_name,
        build_num,
        'PR: <a href="%s">%s</a>' % (link, title))


@hook('before_request')
def strip_path():
    request.environ['PATH_INFO'] = request.environ['PATH_INFO'].rstrip('/')


@post('/bitbucket-pr-webhook')
def bitbucket_pr_webhook():
    event_type = request.headers.get('X-Event-Key')

    if not request.query.jobs:
        return abort(400, 'You must specify the Jenkins jobs to trigger with '
                          'the "jobs" query parameter')

    jobs = request.query.jobs.split(',')

    pr = request.json

    logging.debug("Bitbucket PR hook received:\n%s", pformat(pr, width=1))

    if event_type in ['pullrequest:created', 'pullrequest:updated']:
        if pr['pullrequest']['state'] != "OPEN":
            return 'Ignoring webhook since PR is not open'

        source_commit = pr['pullrequest']['source']['commit']['hash']
        pr_link = pr['pullrequest']['links']['html']['href']
        pr_title = pr['pullrequest']['title']

        owner, repo_slug = pr['repository']['full_name'].split('/')

        jenkins_client.setup_notification_plugin("http://%s" % request.headers['HOST'], jobs)

        pr_metadata = PRMetadata.fetch_by_commit_hash(source_commit) or \
             PRMetadata(commit_hash=source_commit, jobs_triggered=[])

        pr_metadata.title = pr_title
        pr_metadata.link = pr_link
        pr_metadata.save()

        for job_name in jobs:
            if job_name in pr_metadata.job_to_build_num:
                set_jenkins_build_description(job_name,
                                              pr_metadata.job_to_build_num[job_name],
                                              pr_metadata.link,
                                              pr_metadata.title)

            if job_name not in pr_metadata.jobs_triggered:
                jenkins_client.start_build(job_name, source_commit, pr_title, pr_link)
                bb_client.notify_build_changed(owner, repo_slug,
                                               revision=source_commit,
                                               status=bb_client.BUILD_IN_PROGRESS,
                                               job_name=job_name)
                pr_metadata.jobs_triggered.append(job_name)
                pr_metadata.save()
    else:
        return abort(400, 'The event %s is not supported' % event_type)



def parse_repo_fields(repo_url):
    _, path = repo_url.split(':')
    owner, repo = path.strip('/').split('/')
    return owner, re.sub(r'\.git$', '', repo)


@post('/jenkins-notifier')
def jenkins_notifier():
    job_note = request.json

    logging.info("Jenkins Notification Received:\n%s", pformat(job_note, width=1))

    revision = job_note['build']['scm']['commit']
    job_name = job_note['name']
    build_num = job_note['build']['number']

    status = job_note['build'].get('status')
    phase = job_note['build']['phase']
    queue_id = job_note['build']['queue_id']

    if phase == "STARTED":
        bb_state = bb_client.BUILD_IN_PROGRESS
        pr_metadata = PRMetadata.fetch_by_commit_hash(revision)
        if pr_metadata:
            set_jenkins_build_description(
                job_name,
                build_num,
                pr_metadata.link, pr_metadata.title)
            pr_metadata.job_to_build_num[job_name] = build_num
            pr_metadata.save()
    elif phase in ["COMPLETED", "FINALIZED"] and status == "SUCCESS":
        bb_state = bb_client.BUILD_SUCCESSFUL
    elif status == "FAILURE":
        bb_state = bb_client.BUILD_FAILED
    else:
        return abort(400, "Unknown status (%s) and phase (%s) combination" %
                     (status, phase))

    job_url = job_note['build']['full_url']

    owner, repo_slug = parse_repo_fields(job_note['build']['scm']['url'])

    bb_client.notify_build_changed(owner, repo_slug, revision, bb_state,
                                   job_name, job_url)


app = default_app()
