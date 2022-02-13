#!flask/bin/python
from flask import Flask, request, jsonify
from flask_cors import CORS, cross_origin

import re
import sys
import csv

import pymorphy2

#Wikidata sections
from SPARQLWrapper import SPARQLWrapper, JSON
from wikidata.client import Client

from entity_dictionary import entity_dict 
from predicate_dictionary import predicate_dict
from stopwords_dictionary import stopwords
 
app = Flask(__name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'

endpoint_url = "https://query.wikidata.org/sparql"

#Для стоп-слов используем структуру данных set, так как она работает быстрее list
stops = set(stopwords) 

def lemmatize(words):
      res = []
      morph = pymorphy2.MorphAnalyzer()
      for word in words:
        p = morph.parse(word)[0]
        res.append(p.normal_form)
      return res

def get_results(endpoint_url, query):
    user_agent = "WDQS-example Python/%s.%s" % (sys.version_info[0], sys.version_info[1])
    sparql = SPARQLWrapper(endpoint_url, agent=user_agent)
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    return sparql.query().convert()

def construct_sparql_from_nl(obj, predicate):
    return   """SELECT ?item ?item_label ?item_description ?pic
                WHERE
                {
                  wd:"""+obj+""" wdt:"""+predicate+""" ?item.
                  OPTIONAL {?item rdfs:label ?item_label}
                  OPTIONAL {?item schema:description ?item_description}
                  OPTIONAL {?item wdt:P18 ?pic}
                  FILTER((lang(?item_label) = "ru") && (lang(?item_description) = "ru") )
                  #FILTER((lang(?item_label) = "en") || (lang(?item_label) = "ru") )
                  #FILTER((lang(?item_description) = "en") || (lang(?item_description) = "ru") )
                }
                """
select_dict = []
def construct_select_section(select_json):
    result = ""
    select_dict.clear()
    for key in select_json:
        select_dict.append(select_json[key].lower())
        result += "?"+select_json[key].lower()+" "
    #print(result)
    #print(select_dict)
    return result

def construct_body_section(body_json):
    result = ""
    for triple_key in body_json:
        triple = body_json[triple_key]

        subject = triple["subject"].lower()
        predicate = triple["predicate"].lower()
        obj = triple["object"].lower()

        if subject in select_dict:
            subject = "?"+subject
        if predicate in select_dict:
            predicate = "?"+predicate
        if obj in select_dict:
            obj = "?"+obj

        if subject in entity_dict:
            subject = "wd:"+entity_dict[subject] 
        if predicate in predicate_dict:
            predicate = "wdt:"+predicate_dict[predicate]
        if obj in entity_dict:
            obj = "wd:"+entity_dict[obj] 
        result += subject + " " + predicate + " " + obj + ".\n"
    return result

def construct_sparql_manual(select_section, body_section):
    return   """SELECT """ + select_section + """ WHERE{ """+body_section+"""}"""

def get_norm_tokens(query):
    #Оставляем в запросе только буквы       
    letters_only = re.sub("[^а-яА-яa-zA-z]", " ", query) 
    
    #Переводим в нижний регистр и разбиваем на слова
    words = letters_only.lower().split() 

    #фильтруем слова
    words = [w for w in words if not w in stops] 
    #приводим к начальной форме
    words = lemmatize(words)
    return words

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

    key_words = get_norm_tokens(nl_query)
    obj = ""
    predicate = ""
    for word in key_words:
      if word in predicate_dict:
        predicate = predicate_dict[word]
      if word in entity_dict:
        obj = entity_dict[word]

    sparql_query = construct_sparql_from_nl(obj, predicate)

    response = extract_results_from_response(sparql_query)

    return jsonify(response)

@app.route('/', methods=['POST'])
def query_from_constructur():
    select_section = construct_select_section(request.json['select_section'])
    body_section = construct_body_section(request.json['body_section'])
    sparql_query = construct_sparql_manual(select_section, body_section)
    response = extract_results_from_response(sparql_query)
    return jsonify(response)

if __name__ == '__main__':
    app.run(debug=True)






