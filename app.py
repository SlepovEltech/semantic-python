#!flask/bin/python

#web components
from flask import Flask, request, jsonify
from flask_cors import CORS, cross_origin

import re
import sys
import csv

import pymorphy2

#Wikidata section
from SPARQLWrapper import SPARQLWrapper, JSON
from wikidata.client import Client

#dictionary section
from entity_dictionary import entity_dict 
from predicate_dictionary import predicate_dict

#query translators
from QueryConstructor import GUIConstructor 
from QueryConstructor import NLPConstructor

app = Flask(__name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'

endpoint_url = "https://query.wikidata.org/sparql"

if __name__ == '__main__':
    app.run(debug=True)

@app.route('/autocomplete/entity')
def entity_autocomplete():
    substr = str(request.args.get('substr'))
    return jsonify(find_entity_by_substring(substr))

@app.route('/autocomplete/predicate')
def predicate_autocomplete():
    substr = str(request.args.get('substr'))
    substr = str(substr)
    return jsonify(find_predicate_by_substring(substr))


@app.route('/')
def nl_query():
    nl_query = request.args.get('query')

    sparql_query = NLPConstructor(nl_query).get_sparql_query()

    response = extract_results_from_response(sparql_query)

    return jsonify(response)

@app.route('/', methods=['POST'])
def query_from_constructur():
    sparql_query = GUIConstructor(request.json).get_sparql_query()
    print(sparql_query)
    response = extract_results_from_response(sparql_query)
    return jsonify(response)

def get_results(endpoint_url, query):
    user_agent = "WDQS-example Python/%s.%s" % (sys.version_info[0], sys.version_info[1])
    sparql = SPARQLWrapper(endpoint_url, agent=user_agent)
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    return sparql.query().convert()

def extract_results_from_response(sparql_query:str):
    results = get_results(endpoint_url, sparql_query)
    response = []
    for result in results["results"]["bindings"]:
        print(result)
        response.append(result)
    return response

def find_entity_by_substring(substr:str):
    result = []
    for key in entity_dict.keys():
        if(key.find(substr) != -1):
            result.append(key)
    return result

def find_predicate_by_substring(substr:str):
    result = []
    for key in predicate_dict.keys():
        if(key.find(substr) != -1):
            result.append(key)
    return result





