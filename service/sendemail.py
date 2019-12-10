from flask import Flask, request, jsonify
from flask_mail import Message, Mail
from sesamutils import sesam_logger, VariablesConfig
from sesamutils.flask import serve

from datetime import datetime

import sys
import os

# Import smtplib for the actual sending function
import smtplib

# Import the email modules we'll need
from email.message import EmailMessage
from collections import OrderedDict

app = Flask(__name__)

logger = sesam_logger('smtp-bundle', app=app, timestamp=True)

required_env_vars = ["MAIL_SERVER","SENDER","RCPT","MAIL_PASSWORD","MAIL_USERNAME"]
optional_env_vars = [("MAIL_PORT",587),("LOG_LEVEL","info"),("MAIL_USE_TLS", True),("MAIL_USE_SSL", False),("BUNDLE_SIZE", 2)]
config = VariablesConfig(required_env_vars, optional_env_vars=optional_env_vars)

mail = Mail(app)

def send_mail(subject,to,sender,body):
    logger.debug("send mail routine")
    msg = EmailMessage()
    msg.set_content(body)
    msg['Subject'] = subject
    msg['From'] = sender
    msg['To'] = to

    logger.debug("Connecting to SMTP: " + config.MAIL_SERVER)
    try:
        s = smtplib.SMTP(config.MAIL_SERVER, config.MAIL_PORT, timeout=30)
    except Exception as e:
        logger.error("Error during connection to server: {}".format(e))
        return "Error: {}\n".format(e)

    logger.debug("logging to server: " + config.MAIL_SERVER)
    try:
        s.login(config.MAIL_USERNAME, config.MAIL_PASSWORD)
    except Exception as e:
        logger.error("Error during logon to server: {}".format(e))
        return "Error: {}\n".format(e)

    logger.debug("Sending \"" + msg['Subject'] + "\"")
    try:
        s.send_message(msg)
    except Exception as e:
        logger.error("Error encountered sending the email: {}".format(e))
    s.quit()
    logger.debug("\"" + msg['Subject'] + "\" sent")


@app.route('/truc', methods=['GET','POST'])
def send_decorated_email():
    logger.debug("\n\nalternative email requested\n")

#    logger.debug("Hello Alice\n\n" + "\tSMTP\t" + config.MAIL_SERVER + "\n\tSENDER\t" + config.SENDER + "\n\tRCPT\t" + config.RCPT + "\n\tPORT\t" + str(config.MAIL_PORT) + "\n\tDebug\t" + config.LOG_LEVEL)


#    msg = Message('From Sesam using the other library', sender=config.SENDER, recipients=[config.RCPT])
#    msg.body = "Hello Alice\n\n" + "\tSMTP\t" + config.MAIL_SERVER + "\n\tSENDER\t" + config.SENDER + "\n\tRCPT\t" + config.RCPT + "\n\tPORT\t" + str(config.MAIL_PORT) + "\n\tDebug\t" + config.LOG_LEVEL
#    try:
#        mail.send(msg)
#    except Exception as e:
#        logger.error("Error sending: {}".format(e))
#        logger.debug("Using:\n\t" + config.MAIL_USERNAME + "\n\t" + config.MAIL_PASSWORD)
#        return "Error: {}\n".format(e) + "Using:\n\t" + config.MAIL_USERNAME + "\n\t" + config.MAIL_PASSWORD + "\n"

#    logger.debug("\n\t " + "From Sesam using the other library" + " sent")
    return "alternative email Sent\n"

@app.route('/', methods=['GET','POST'])
def send_email():
    entities = request.get_json()

    logger.debug(str(len(entities)) + " entities to work with")
    if len(entities) > int(config.BUNDLE_SIZE):
        send_mail('Bundle of errors', config.RCPT, config.SENDER, "There are " + str(len(entities)) + " entities failling, too many")
    else:
        for entity in entities:
            body = str(entity)
            logger.debug("Entity : " + str(entity))
            send_mail('SMTP from Sesam', config.RCPT, config.SENDER, body)

#    return '[{"_id": "0", "message": "generic email Sent"}]'
    return 'essai avec juste une string'

if __name__ == '__main__':

    if not config.validate():
        logger.error("Fatal Error, env. not set properly")
        os.sys.exit(1)

    logger.debug("\n\tSMTP\t" + config.MAIL_SERVER + "\n\tSENDER\t" + config.SENDER + "\n\tRCPT\t" + config.RCPT + "\n\tPORT\t" + str(config.MAIL_PORT) + "\n\tDebug\t" + config.LOG_LEVEL)
    # This is used when running locally. Gunicorn is used to run the
    # application on Google App Engine. See entrypoint in app.yaml.
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)
