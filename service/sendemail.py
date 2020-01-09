from flask import Flask, request, Response, jsonify
from flask_mail import Message, Mail
from sesamutils import sesam_logger, VariablesConfig
import os

import requests
import json

# Import smtplib for the actual sending function
import smtplib

# Import the email modules we'll need
from email.message import EmailMessage
from collections import OrderedDict

app = Flask(__name__)

logger = sesam_logger('smtp-bundle', app=app, timestamp=True)

required_env_vars = ["MAIL_SERVER","SENDER","RCPT","MAIL_PASSWORD","MAIL_USERNAME","SESAM_JWT","BASE_URL"]
optional_env_vars = [("MAIL_PORT",587),("LOG_LEVEL","info"),("MAIL_USE_TLS", True),("MAIL_USE_SSL", False),("BUNDLE_SIZE", 2),("SEND_UNTIL_FIXED", False)]
config = VariablesConfig(required_env_vars, optional_env_vars=optional_env_vars)

mail = Mail(app)

def stream_json(entities):
    first = True
    yield '['
    for i, row in enumerate(entities):
        if not first:
            yield ','
        else:
            first = False
        yield json.dumps(row)
    yield ']'


def find_key_string(dictionary):
    string = ""
    for i, key in enumerate(dictionary.keys()):
        try:
            if len(dictionary[key].keys()) != 0:
                string +="\n" + key + ": " + "{" + find_key_string(dictionary[key]) + "}"
            else:
                string +="\n" + key + ": " + dictionary[key]
        except AttributeError:
            string += "\n" + key + ": " + str(dictionary[key])
        if i != len(dictionary.keys())-1:
            string += ","
    return string

def send_mail(subject,to,sender,body):
    msg = EmailMessage()
    msg.set_content(body)
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = to

    try:
        s = smtplib.SMTP(config.MAIL_SERVER, config.MAIL_PORT, timeout=30)
    except Exception as e:
        logger.error("Error during connection to server: {}".format(e))
        return "Error: {}\n".format(e)

    try:
        s.login(config.MAIL_USERNAME, config.MAIL_PASSWORD)
    except Exception as e:
        logger.error("Error during logon to server: {}".format(e))
        return "Error: {}\n".format(e)

    try:
        s.send_message(msg)
    except Exception as e:
        logger.error("Error encountered sending the email: {}".format(e))
    s.quit()

@app.route('/notify/<string:pipe>/<string:reason>/<string:mail_header>', methods=['GET','POST'])
def notify(pipe, reason, mail_header):
    entities = request.get_json()

    logger.debug(str(len(entities)) + " entities to work with")
    if len(entities) > int(config.BUNDLE_SIZE):
        send_mail('Numerous errors encountered while processing ' + pipe, config.RCPT, config.SENDER, "There are " + str(len(entities)) + " entities failing because " + reason + "\n" + mail_header + "\n")
    else:
        for entity in entities:
            body = str(entity) + "\n\tPayload:\n" + find_key_string(entity['entity']['payload'])
            logger.debug("Entity : " + str(entity))
            send_mail('SMTP from Sesam regarding ' + pipe, config.RCPT, config.SENDER, body + "\n" + reason + "\n" + mail_header + "\n")

    if(config.SEND_UNTIL_FIXED == "True"):
        header = {'Authorization': "Bearer {}".format(config.SESAM_JWT)}
        logger.debug("Resetting pump {}".format(pipe))
        payload = {'operation': 'update-last-seen', 'last-seen': ''}
        resp = requests.post(config.BASE_URL + "/pipes/%s/pump" % pipe, headers=header, data=payload)
        if resp.status_code != 200:
            logger.error("Error in post to Sesam: status_code = {} for _id: {}".format(resp.text, entity['_id']))
        logger.debug("Starting pump {}".format(pipe))
        payload = {'operation': 'start'}
        resp = requests.post(config.BASE_URL + "/pipes/%s/pump" % pipe, headers=header, data=payload)
        if resp.status_code != 200:
            logger.error("Error in post to Sesam: status_code = {} for _id: {}".format(resp.text, entity['_id']))

    return Response(stream_json(entities), mimetype='application/json')

@app.route('/reset_pump/<string:pipe>', methods=['GET','POST'])
def reset_pump(pipe):
    entities = request.get_json()

    if(config.SEND_UNTIL_FIXED == "True"):
        header = {'Authorization': "Bearer {}".format(config.SESAM_JWT)}
        logger.debug("Resetting pump {}".format(pipe))
        payload = {'operation': 'update-last-seen', 'last-seen': ''}
        resp = requests.post(config.BASE_URL + "/pipes/%s/pump" % pipe, headers=header, data=payload)
        if resp.status_code != 200:
            logger.error("Error in post to Sesam: status_code = {} for _id: {}".format(resp.text, entity['_id']))
#        logger.debug("PUMP STATUS: " + requests.get(config.BASE_URL + "/pipes/%s/pump" % pipe, headers={'Authorization': "Bearer {}".format(config.SESAM_JWT)}).text)

#    return Response(stream_json(entities), mimetype='application/json')
    return '[]'

if __name__ == '__main__':

    if not config.validate():
        logger.error("Fatal Error, env. not set properly")
        os.sys.exit(1)

    logger.debug("\n\tSMTP\t" + config.MAIL_SERVER + "\n\tSENDER\t" + config.SENDER + "\n\tRCPT\t" + config.RCPT + "\n\tPORT\t" + str(config.MAIL_PORT) + "\n\tDebug\t" + config.LOG_LEVEL)
    # This is used when running locally. Gunicorn is used to run the
    # application on Google App Engine. See entrypoint in app.yaml.
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
