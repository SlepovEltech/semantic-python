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
from predicate_dictionary import predicate_dict_nlp
from stopwords_dictionary import stopwords
 
app = Flask(__name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'

endpoint_url = "https://query.wikidata.org/sparql"

#Для стоп-слов используем структуру данных set, так как она работает быстрее list
stops = set(stopwords) 

class ManualQuery:
    def __init__(self, request):
        self.select_section = ""
        self.body_section = ""
        self.select_dict = []
        self.construct_select_section(request["select_section"])
        self.construct_body_section(request["body_section"])


    def construct_select_section(self, select_json):
        self.select_section = ""
        self.select_dict.clear()
        for key in select_json:
            self.select_dict.append(select_json[key].lower())
            self.select_section += "?"+select_json[key].lower()+" "
        #print(result)
        #print(select_dict)
    
    def construct_body_section(self, body_json):
        self.body_section = ""
        for triple_key in body_json:
            triple = body_json[triple_key]

            subject = triple["subject"].lower()
            predicate = triple["predicate"].lower()
            obj = triple["object"].lower()

            subject_label = ""
            obj_label = ""
            predicate_label = ""

            if subject in self.select_dict:
                subject = "?"+subject
                subject_label = subject+"_label"
                if(subject_label not in self.select_section):
                    self.select_section += " "+subject_label
            if predicate in self.select_dict:
                predicate = "?"+predicate
                predicate_label = predicate+"_label"
                if(predicate_label not in self.select_section):
                    self.select_section += " "+predicate_label
            if obj in self.select_dict:
                obj = "?"+obj
                obj_label = obj+"_label"
                if(obj_label not in self.select_section):
                    self.select_section += " "+obj_label


            if subject in entity_dict:
                subject = "wd:"+entity_dict[subject] 
            if predicate in predicate_dict:
                predicate = "wdt:"+predicate_dict[predicate]
            if obj in entity_dict:
                obj = "wd:"+entity_dict[obj] 
            self.body_section += subject + " " + predicate + " " + obj + ".\n"

            if(subject_label != ""):
                self.body_section += subject + " rdfs:label " + subject_label + ".\n"
                self.body_section += "FILTER(lang("+subject_label+") = \"en\").\n"
            if(predicate_label != ""):
                self.body_section += predicate + " rdfs:label " + predicate_label + ".\n"
                self.body_section += "FILTER((ang("+predicate_label+") = \"en\").\n"
            if(obj_label != ""):
                self.body_section += obj + " rdfs:label " + obj_label + ".\n"
                self.body_section += "FILTER(lang("+obj_label+") = \"en\").\n"    
    
    def get_sparql_query(self):
        return   """SELECT """ + self.select_section + """ WHERE{ """+self.body_section+"""}"""


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

        subject_label = ""
        obj_label = ""
        predicate_label = ""

        if subject in select_dict:
            subject = "?"+subject
            subject_label = subject+"_label"
        if predicate in select_dict:
            predicate = "?"+predicate
            predicate_label = predicate+"_label"
        if obj in select_dict:
            obj = "?"+obj
            obj_label = obj+"_label"

        if subject in entity_dict:
            subject = "wd:"+entity_dict[subject] 
        if predicate in predicate_dict:
            predicate = "wdt:"+predicate_dict[predicate]
        if obj in entity_dict:
            obj = "wd:"+entity_dict[obj] 
        result += subject + " " + predicate + " " + obj + ".\n"

        if(subject_label != ""):
            result += subject + " rdfs:label " + subject_label + ".\n"
            result += "FILTER(lang("+subject_label+") = \"ru\").\n"
        if(predicate_label != ""):
            result += predicate + " rdfs:label " + predicate_label + ".\n"
            result += "FILTER((ang("+predicate_label+") = \"ru\").\n"
        if(obj_label != ""):
            result += obj + " rdfs:label " + obj_label + ".\n"
            result += "FILTER(lang("+obj_label+") = \"ru\").\n"    
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
      if word in predicate_dict_nlp:
        predicate = predicate_dict_nlp[word]
      if word in entity_dict:
        obj = entity_dict[word]

    sparql_query = construct_sparql_from_nl(obj, predicate)

    response = extract_results_from_response(sparql_query)

    return jsonify(response)

@app.route('/', methods=['POST'])
def query_from_constructur():
    # select_section = construct_select_section(request.json['select_section'])
    # body_section = construct_body_section(request.json['body_section'])
    # sparql_query = construct_sparql_manual(select_section, body_section)
    sparql_query = ManualQuery(request.json).get_sparql_query()
    print(sparql_query)
    response = extract_results_from_response(sparql_query)
    return jsonify(response)

if __name__ == '__main__':
    app.run(debug=True)






