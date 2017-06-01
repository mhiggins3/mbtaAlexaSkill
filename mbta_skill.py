"""
MBTA commuter rail skill that gets service alerts and next train times. 
"""

from __future__ import print_function
from array import *
import random
import uuid
import boto3
import json
import urllib2
import urllib
import decimal
import logging
import re

logger = logging.getLogger()
logger.setLevel(logging.INFO)
mbta_key = "XMDOVVmpt0CqZQkOuZuqeQ"
mbta_base_url = "http://realtime.mbta.com/developer/api/v2/"
# --------------- Helpers that build all of the responses ----------------------

def build_speechlet_response(title, output, reprompt_text, should_end_session):
    return {
        'outputSpeech': {
            'type': 'PlainText',
            'text': output
        },
        'card': {
            'type': 'Simple',
            'title': "SessionSpeechlet - " + title,
            'content': "SessionSpeechlet - " + output
        },
        'reprompt': {
            'outputSpeech': {
                'type': 'PlainText',
                'text': reprompt_text
            }
        },
        'shouldEndSession': should_end_session
    }


def build_response(session_attributes, speechlet_response):
    return {
        'version': '1.0',
        'sessionAttributes': session_attributes,
        'response': speechlet_response
    }

# --------------- Functions that control the skill's behavior ------------------

def get_welcome_response():
    """ If we wanted to initialize the session to have some attributes we could
    add those here
    """

    session_attributes = {}
    card_title = "Welcome"
    speech_output = "Welcome M.B.T.A info. " \
                    "You can ask me when the next trip is for a given stop " \
                    "or ask if their are any alerts for a given line?" 
    # If the user either does not reply to the welcome message or says something
    # that is not understood, they will be prompted again with this text.
    reprompt_text = "Say when is the next trip for a given stop, " \
                    "or ask if their are any alterts for a given line"
    should_end_session = False

    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, reprompt_text, should_end_session))


def handle_session_end_request():
    card_title = "Session Ended"
    speech_output = "Thanks for playing! " 

    # Setting this to true ends the session and exits the skill.
    should_end_session = True
    return build_response({}, build_speechlet_response(
        card_title, speech_output, None, should_end_session))

def get_alert_data(session, mbta_line):

    url = mbta_base_url + "alerts?api_key=" + mbta_key + "&include_access_alerts=false&include_service_alerts=true&format=json"
    logger.info(url)
    response = urllib2.urlopen(url);
    alerts = json.load(response, parse_float = decimal.Decimal)
    line_regexp = re.compile(".*" + mbta_line + ".*") 
    rv = {}
    for alert in alerts['alerts']:
        if alert['alert_lifecycle'] == "New":
            affected_services = alert['affected_services']['services']
            for affected_service in affected_services:
                if 'route_name' in affected_service and line_regexp.match(affected_service['route_name']):
                    rv[alert['alert_id']] = alert

    return rv 



def find_alerts(intent, session):
    """ Looks up alerts for a given line
    """

    card_title = intent['name']
    session_attributes = {}
    should_end_session = False

    if 'Line' in intent['slots']:
        mbta_line = intent['slots']['Line']['value']
        alert_data = get_alert_data(session, mbta_line)
        speech_output = "Ok I have found the following alerts " + str(len(alert_data)) + " for " + mbta_line + ". "
        logger.info(speech_output)
        for key , alert in alert_data.iteritems():
            speech_output += alert['header_text'] + ". "    
            
        reprompt_text = "You can hear alerts by saying, " \
            "are there any alerts for the Worcester line?"

    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, reprompt_text, should_end_session))

def next_trip(intent, session):
    
    card_title = intent['name']
    session_attributes = {}
    should_end_session = False

    if 'Line' in intent['slots']:
        mbta_stop = intent['slots']['Stop']['value']
        speech_output = "I have found the following trips from " + \
            mbta_stop + \
            ". bala bla "
        reprompt_text = "You can find out the next trips from at a stop by asking " \
            "when is the next train leaving Worcester?"

    return build_response(session_attributes, build_speechlet_response(
        card_title, speech_output, reprompt_text, should_end_session))

# --------------- Events ------------------

def on_session_started(session_started_request, session):
    """ Called when the session starts """

    print("on_session_started requestId=" + session_started_request['requestId']
          + ", sessionId=" + session['sessionId'])


def on_launch(launch_request, session):
    """ Called when the user launches the skill without specifying what they
    want
    """

    print("on_launch requestId=" + launch_request['requestId'] +
          ", sessionId=" + session['sessionId'])
    # Dispatch to your skill's launch
    return get_welcome_response()


def on_intent(intent_request, session):
    """ Called when the user specifies an intent for this skill """

    print("on_intent requestId=" + intent_request['requestId'] +
          ", sessionId=" + session['sessionId'])

    intent = intent_request['intent']
    intent_name = intent_request['intent']['name']
    logger.info(json.dumps(session))
    # Dispatch to your skill's intent handlers
    if intent_name == "FindAlertsIntent":
        return find_alerts(intent, session)
    elif intent_name == "NextTripIntent":
        return next_trip(intent, session)
    elif intent_name == "AMAZON.HelpIntent":
        return get_welcome_response()
    elif intent_name == "AMAZON.CancelIntent" or intent_name == "AMAZON.StopIntent":
        return handle_session_end_request()
    else:
        raise ValueError("Invalid intent " + intent_name)


def on_session_ended(session_ended_request, session):
    """ Called when the user ends the session.

    Is not called when the skill returns should_end_session=true
    """
    print("on_session_ended requestId=" + session_ended_request['requestId'] +
          ", sessionId=" + session['sessionId'])
    # add cleanup logic here


# --------------- Main handler ------------------

def lambda_handler(event, context):
    """ Route the incoming request based on type (LaunchRequest, IntentRequest,
    etc.) The JSON body of the request is provided in the event parameter.
    """
    print("event.session.application.applicationId=" +
          event['session']['application']['applicationId'])

    """
    Uncomment this if statement and populate with your skill's application ID to
    prevent someone else from configuring a skill that sends requests to this
    function.
    """
    # if (event['session']['application']['applicationId'] !=
    #         "amzn1.echo-sdk-ams.app.[unique-value-here]"):
    #     raise ValueError("Invalid Application ID")

    if event['session']['new']:
        on_session_started({'requestId': event['request']['requestId']},
                           event['session'])

    if event['request']['type'] == "LaunchRequest":
        return on_launch(event['request'], event['session'])
    elif event['request']['type'] == "IntentRequest":
        return on_intent(event['request'], event['session'])
    elif event['request']['type'] == "SessionEndedRequest":
        return on_session_ended(event['request'], event['session'])

