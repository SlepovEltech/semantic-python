from entity_dictionary import entity_dict 
from predicate_dictionary import predicate_dict
from predicate_dictionary import predicate_dict_nlp
from stopwords_dictionary import stopwords

import re
import sys
import csv

#Set is faster then list
stops = set(stopwords)
 
import pymorphy2
class GUIConstructor:
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
                
            if predicate in self.select_dict:
                predicate = "?"+predicate
            
            if obj in self.select_dict:
                obj = "?"+obj
        
            if predicate in predicate_dict:
                if predicate != 'label' and predicate != 'description':
                    predicate = "wdt:"+predicate_dict[predicate]
                else:
                    predicate = predicate_dict[predicate]
                    rdfs_pred = obj
            if subject in entity_dict:
                subject = "wd:"+entity_dict[subject] 
            if obj in entity_dict:
                obj = "wd:"+entity_dict[obj] 
            self.body_section += subject + " " + predicate + " " + obj + ".\n"
            
            if(('rdfs' in predicate) or ('schema' in predicate)):
                self.body_section += "FILTER(lang("+rdfs_pred+") = \"en\").\n"
           
    def get_sparql_query(self):
        return   """SELECT """ + self.select_section + """ WHERE{ """+self.body_section+"""}"""


class NLPConstructor:
    def __init__(self, query):
        self.query = query
        self.key_words = self.get_norm_tokens()

        self.subject = ""
        self.predicate = ""

        for word in self.key_words:
            if word in predicate_dict_nlp:
                self.predicate = predicate_dict_nlp[word]
            if word in entity_dict:
                self.subject = entity_dict[word]

    def get_sparql_query(self):
        return   """SELECT ?item ?item_label ?item_description ?pic
                WHERE
                {
                  wd:"""+self.subject+""" wdt:"""+self.predicate+""" ?item.
                  OPTIONAL {?item rdfs:label ?item_label}
                  OPTIONAL {?item schema:description ?item_description}
                  OPTIONAL {?item wdt:P18 ?pic}
                  FILTER((lang(?item_label) = "ru") && (lang(?item_description) = "ru") )
                  #FILTER((lang(?item_label) = "en") || (lang(?item_label) = "ru") )
                  #FILTER((lang(?item_description) = "en") || (lang(?item_description) = "ru") )
                }
                """
    def get_norm_tokens(self):
        #Оставляем в запросе только буквы       
        letters_only = re.sub("[^а-яА-яa-zA-z]", " ", self.query) 
        
        #Переводим в нижний регистр и разбиваем на слова
        words = letters_only.lower().split() 

        #фильтруем слова
        words = [w for w in words if not w in stops] 
        #приводим к начальной форме
        words = self.lemmatize(words)
        return words

    def lemmatize(self, words):
        res = []
        morph = pymorphy2.MorphAnalyzer()
        for word in words:
            p = morph.parse(word)[0]
            res.append(p.normal_form)
        return res