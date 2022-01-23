#!flask/bin/python
from flask import Flask, request, jsonify
from flask_cors import CORS, cross_origin

import re
import sys
import csv

#NLP section
#import nltk
#from nltk.corpus import stopwords
nltk.download('stopwords')
import pymorphy2

#Wikidata sections
from SPARQLWrapper import SPARQLWrapper, JSON
from wikidata.client import Client


from dictionary import entity_dict, predicate_dict

app = Flask(__name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'

endpoint_url = "https://query.wikidata.org/sparql"

#Для стоп-слов используем структуру данных set, так как она работает быстрее list
stops = set(stopwords.words("russian")) 

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

def construct_sparql(obj, predicate):
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

@app.route('/')
def index():
    nl_query = request.args.get('query')

    key_words = get_norm_tokens(nl_query)
    obj = ""
    predicate = ""
    for word in key_words:
      if word in predicate_dict:
        predicate = predicate_dict[word]
      if word in entity_dict:
        obj = entity_dict[word]

    sparql_query = construct_sparql(obj, predicate)
    results = get_results(endpoint_url, sparql_query)
    response = []
    for result in results["results"]["bindings"]:
        print(result)
        response.append(result)

    return jsonify(response)

if __name__ == '__main__':
    app.run(debug=True)






