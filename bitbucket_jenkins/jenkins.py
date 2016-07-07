import base64
import logging
from mako.template import Template
import os
import requests
from urllib.parse import urljoin

from jenkinsapi.jenkins import Jenkins


this_script_dir = os.path.dirname(os.path.abspath(__file__))


class GroovyError(Exception):
    pass


class JenkinsGroovy():
    def __init__(self, jenkins_url, username, password):
        self.jenkins_url = jenkins_url
        self.username = username
        self.password = password

    def _read_script(self, script_name):
        """
        Returns a 2-tuple with the script content and a token that should appear in
        the output when the script is finished indicating that it finished
        executing without exception
        """
        with open(os.path.join(this_script_dir, 'groovy/', script_name)) as f:
            content = f.read()

        token = base64.b64encode(os.urandom(16)).decode('utf-8')

        return content + '\nprintln("{0}");'.format(token), token

    def _do_script_request(self, script_content):
        logging.debug("Submitting script to Jenkins:\n%s" % script_content)

        script_url = urljoin(self.jenkins_url, '/scriptText')

        resp = requests.post(script_url, data={"script": script_content},
                            auth=(self.username, self.password))

        logging.debug("Groovy output from Jenkins:\n%s" % resp.content)

        return resp.content.decode('utf-8')

    def run(self, script_path, script_vars={}):
        script_content, token = self._read_script(script_path)
        rendered_script = Template(script_content).render(**script_vars)

        output = self._do_script_request(rendered_script)

        if token not in output:
            raise GroovyError("Finished token not found in output:\n%s" % output)
        else:
            return output


class JenkinsClient():
    def __init__(self, jenkins_url, username, password):
        self.groovy = JenkinsGroovy(jenkins_url, username, password)
        self.client = Jenkins(jenkins_url, username, password)

    def start_build(self, job_name, commit_id, pr_title, pr_link):
        logging.info("Invoking Jenkins build for job %s, commit_id=%s" %
                     (job_name, commit_id))
        queue_item = self.client[job_name].invoke(build_params=dict(revision=commit_id))

    def setup_notification_plugin(self, notifier_base_url, job_names):
        self.groovy.run('add_notification_plugin.groovy',
                        {"notification_url": urljoin(notifier_base_url, '/jenkins-notifier/'),
                         "job_names": job_names})
