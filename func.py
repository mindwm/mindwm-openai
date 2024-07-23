from parliament import Context

import requests
import cloudevents
from cloudevents.http import from_http, CloudEvent
import sys
import os
from neomodel import config
from neo4j import GraphDatabase

from neomodel import (config, StructuredNode, StringProperty, IntegerProperty,
	UniqueIdProperty, RelationshipTo, RelationshipFrom, Relationship, One, OneOrMore,
    DateTimeProperty)
from neomodel.properties import JSONProperty
from neomodel import db

from openai import OpenAI

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
)
model_engine = "gpt-4"

neo4j_url = os.getenv("NEO4J_URL")
neo4j_username = os.getenv("NEO4J_USERNAME")
neo4j_password = os.getenv("NEO4J_PASSWORD")

config.DATABASE_URL = f"bolt://{neo4j_username}:{neo4j_password}@{neo4j_url}"
config.DRIVER = GraphDatabase.driver(f"bolt://{neo4j_url}")

class MindwmUser(StructuredNode):
    username = StringProperty(required = True)
    host = RelationshipTo('MindwmHost', 'HAS_MINDWM_HOST')

class MindwmHost(StructuredNode):
    hostname = StringProperty(required = True)
    tmux = RelationshipTo('Tmux', 'HAS_TMUX', cardinality=OneOrMore)

class Tmux(StructuredNode):
    socket_path = StringProperty(required = True)
    host_id = IntegerProperty(required = True)
    host = RelationshipFrom('MindwmHost', 'HAS_TMUX', cardinality=One)
    session = RelationshipTo('TmuxSession', 'HAS_TMUX_SESSION', cardinality=OneOrMore)

class TmuxSession(StructuredNode):
    name = StringProperty(required = True)
    tmux_id = IntegerProperty(required = True)
    socket_path = RelationshipFrom('Tmux', 'HAS_TMUX', cardinality=One)
    pane = RelationshipTo('TmuxPane', 'HAS_TMUX_PANE', cardinality=OneOrMore)

class TmuxPane(StructuredNode):
    pane_id = IntegerProperty(required = True)
    session_id = IntegerProperty(required = True)
    session = RelationshipFrom('TmuxSession', 'HAS_TMUX_PANE', cardinality=One)
    title = StringProperty()
    contextParameters = JSONProperty(default={})
    io_document = Relationship('IoDocument', 'HAS_IO_DOCUMENT')

class IoDocument(StructuredNode):
    uuid = StringProperty(unique_index=True, required = True)
    user_input = StringProperty(required = True)
    output = StringProperty(required = True)
    ps1 = StringProperty(required = True)
    time = DateTimeProperty(default_now = True)
    tmux_pane = Relationship('TmuxPane', 'HAS_IO_DOCUMENT')

def main(context: Context):
    """
    Function template
    The context parameter contains the Flask request object and any
    CloudEvent received with the request.
    """
    event = from_http(context.request.headers, context.request.data)
    data = event.data
    payload = data['payload']
    end = payload['end']
    id = end['id']


    results, meta = db.cypher_query(f"MATCH (n:IoDocument) WHERE ID(n) = {id}  RETURN n;")
    iodoc = IoDocument.inflate(results[meta.index('n')][0])
    user_input = iodoc.user_input
	

    if "# chatgpt" in user_input:
        user_input = user_input.replace("# chatgpt", "").strip()

        tmux_pane = iodoc.tmux_pane.get()
        element_id = tmux_pane.element_id
        results, meta = results, meta = db.cypher_query(f"MATCH (pane:TmuxPane)-[:HAS_IO_DOCUMENT]->(doc:IoDocument) WHERE ID(pane) = {element_id} RETURN doc")
        if len(results) <= 1:
            print("previous message was not found", file=sys.stderr)
            return "", 200

        results, meta = db.cypher_query(f"MATCH (pane:TmuxPane)-[:HAS_IO_DOCUMENT]->(doc:IoDocument) WHERE ID(pane) = {element_id} RETURN doc ORDER BY doc.time DESC SKIP 1 LIMIT 1") 
         
        iodoc2 = IoDocument.inflate(results[meta.index('doc')][0])

        input_text = user_input + "\n\n" + iodoc2.output
        if "prompt" in tmux_pane.contextParameters:
            prompt = tmux_pane.contextParameters["prompt"]
            input_text = prompt + "\n" + input_text
        
        endpoint = ""

        data = {}
        headers = {}
        if "OPENAI_ENDPOINT" in tmux_pane.contextParameters:
            endpoint = tmux_pane.contextParameters["OPENAI_ENDPOINT"]
            data = {"model": "llama-3-instruct-70b", "messages": [{"role": "user", "content": input_text}]}
            headers = {"Content-Type": "application/json"}
        else:
            if "OPENAI_TOKEN" not in tmux_pane.contextParameters:
                print("OPENAI_TOKEN is empty", file=sys.stderr)

                return "", 200
            openai_token = tmux_pane.contextParameters["OPENAI_TOKEN"]
            endpoint = "https://api.openai.com/v1/chat/completions"
            data = {"model": "gpt-4", "messages": [{'role': 'user', 'content': input_text}]}
            headers = {"Content-Type": "application/json", 'Authorization': f"Bearer {openai_token}"}

        responseJSON = make_request(endpoint, headers, data)
        if not responseJSON:
            print("failed to make request", file=sys.stderr)
            return "", 200

        answer = responseJSON["choices"][0]["message"]["content"]

        attrs = {"specversion": "1.0", "type": "openai.service.output", "source": "/openai-service", "datacontenttype": "application/json"}
        data = {"chatgpt_answer": answer}


        output_event = CloudEvent(attrs, data)
        
        headers, body = cloudevents.conversion.to_structured(output_event)
        print(body, file=sys.stderr)
        print(headers, file=sys.stderr)

        return body, 200, headers



    return "", 200


def make_request(endpoint, headers, data):
    try:
        response = requests.post(endpoint, headers=headers, json=data)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.HTTPError as http_err:
        print(f"HTTP error occurred: {http_err}")
    except requests.exceptions.ConnectionError as conn_err:
        print(f"Connection error occurred: {conn_err}")
    except requests.exceptions.Timeout as timeout_err:
        print(f"Timeout error occurred: {timeout_err}")
    except requests.exceptions.RequestException as req_err:
        print(f"An error occurred: {req_err}")
    return None
