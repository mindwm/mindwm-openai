from parliament import Context

import cloudevents
from cloudevents.http import from_http, CloudEvent
import sys
import os
from neomodel import config
from neo4j import GraphDatabase

from neomodel import (config, StructuredNode, StringProperty, IntegerProperty,
	UniqueIdProperty, RelationshipTo, RelationshipFrom, Relationship, One, OneOrMore,
    DateTimeProperty)
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
        tmux_pane = iodoc.tmux_pane.get()
        element_id = tmux_pane.element_id
        results, meta = results, meta = db.cypher_query(f"MATCH (pane:TmuxPane)-[:HAS_IO_DOCUMENT]->(doc:IoDocument) WHERE ID(pane) = {element_id} RETURN doc")
        if len(results) <= 1:
            return "", 400
  
        results, meta = db.cypher_query(f"MATCH (pane:TmuxPane)-[:HAS_IO_DOCUMENT]->(doc:IoDocument) WHERE ID(pane) = {element_id} RETURN doc ORDER BY doc.time DESC SKIP 1 LIMIT 1") 
         
        iodoc2 = IoDocument.inflate(results[meta.index('doc')][0])

        input_text = user_input + ": " + iodoc2.output
        chat_completion = client.chat.completions.create(model=model_engine, messages=[{"role": "user", "content": input_text}])
        message = chat_completion.choices[0].message.content

        attrs = {"specversion": "1.0", "type": "openai.service.output", "source": "/openai-service", "datacontenttype": "application/json"}
        data = {"chatgpt_answer": message}

        output_event = CloudEvent(attrs, data)
        
        headers, body = cloudevents.conversion.to_structured(output_event)
        print(body, file=sys.stderr)
        print(headers, file=sys.stderr)
        return body, 200, headers    

    return "", 200
