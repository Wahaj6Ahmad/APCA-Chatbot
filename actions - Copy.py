from typing import Any, Text, Dict, List
from datetime import datetime
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
import random
from typing import Any, Text, Dict, List
import spacy
from rasa_sdk.events import SlotSet
from rasa_sdk.events import AllSlotsReset
from rasa_sdk.events import Restarted
from py2neo import Node, Relationship, Graph
import json
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np
import time

paintings = ["King Caspar","Head of a Boy in a Turban","Don Miguel de Castro, Emissary of Congo","Diego Bemba, a Servant of Don Miguel de Castro","Pedro Sunda, a Servant of Don Miguel de Castro","Map of Paranambucae","Portrait of a Black Girl","Portrait of a Man","Man in a Turban","Doritos","The New Utopia Begins Here: Hermina Huiswoud","The Unspoken Truth","Ilona","Head of a Boy","The Market in Dam Square","Two moors"]
guest_id = "" #keeps track of the guest's unique id
flag_finish_tour = False ## flag to keep track of when the tour has ended
latest_aspect = "" ## keeps track of the aspect guest asked for to use in other functions
init_setting = 0 ## value decides which mixed initiative setting COBY should be in. possible values are [0,1,2,3]
## where 0 is giving the turn to the guest
## where 1 is 2 prompts
## 2 can also be merging name + description of the aspect and then going with 2 prompts
## 3 is asking if user wants more details or give another attribute

# Dictionary to store painting names as keys and linked labels as values
painting_linked_labels = {}

## making a list of painting labels ##
for painting_name in paintings:
    query = GenerateQuery.find_linked_labels_query(painting_name)
    record = GenerateQuery.connect_to_kg(query)
    record["linked_labels"] for record in result
    painting_linked_labels[painting_name] = linked_labels



class ActionNewGuest(Action):
    def name(self) -> Text:
        return "action_new_guest"
    
    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
         print(tracker.latest_message['entities'])

         guestname = tracker.latest_message['entities'][0]['value']
         dispatcher.utter_message(response = "utter_second_greet", name = guestname)
         guesttime = datetime.now()
         global guest_id
         guest_id = str((tracker.current_state())["sender_id"])
         # make a new node in the KG with these details
         create_guest = GenerateQuery.create_new_guest_query(guestname, guesttime)
         GenerateQuery.connect_to_kg(create_guest)
         print("new guest id is: " + guest_id)
        
         return []

class ActionNextPainting(Action):
    def name(self) -> Text:
        return "action_next_painting"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        # Get the intent of the user
        intent = tracker.latest_message['intent']
        print("ActionNextPainting::Intent = " + intent['name']) ##
        painting_number = tracker.get_slot("painting_number")
        global flag_finish_tour
        if painting_number == 16: flag_finish_tour = True
        if painting_number == None: painting_number = 0
        print("ActionNextPainting::current painting id slot = " + str(painting_number)) ##

        painting_name = tracker.get_slot("current_painting")

        if intent['name'] == 'affirmative' or intent['name'] == 'request_next_painting':

            #restart the conversation if all paintings have been viewed
            if flag_finish_tour == True:
                dispatcher.utter_message(text="We have come to the end of the tour. I hope you enjoyed it. Come back again soon.")
                flag_finish_tour = False
                return[Restarted()]
            
            current = paintings[painting_number]
            print("ActionNextPainting::Current Painting = " + current)
            
            query = GenerateQuery.make_connection_query(guest_id, current,"has_VISITED")
            GenerateQuery.connect_to_kg(query)
            # SlotSet("current_painting", current)

            #if it is the first painting
            if painting_number == 0:
                dispatcher.utter_message(response = "utter_painting_one_description", current_painting = current)
            # if it is the last painting
            elif painting_number == 15:
                dispatcher.utter_message("We have arrived at the final painting of this exhibition.")
                dispatcher.utter_message(response = "utter_paintings_description", current_painting = current)
            # for the rest of the paintings
            else:
                dispatcher.utter_message(response = "utter_paintings_description", current_painting = current)

            # if intent['name'] == 'request_next_painting':return [SlotSet("current_painting",current), SlotSet("painting_number", painting_number+1)]

            return [SlotSet("current_painting",current), SlotSet("painting_number", painting_number+1)]

        elif intent['name'] == 'negative':
            dispatcher.utter_message(text="No problem, I'll wait for you until you are ready.")
            return[SlotSet("current_painting", painting_name), SlotSet("painting_number", painting_number)]


#### CODE FOR SHOWING THE CURRENT IMAGE ####

        # query = GenerateQuery.get_painting_query(current)
        # image_url = GenerateQuery.connect_to_kg(query)

        # print(image_url)
        # Create an image message
        # image_message = {
        #     "image": image_url,
        #     "attachment": {
        #         "type": "image",
        #         "url": image_url
        #     }
        # }

        # Send the image message
        # dispatcher.utter_message(text = image_url)

        return []

class RequestAspect(Action):
    def name(self):
        return "action_request_aspect"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        print("RequestAspect :: Executed") ##
        node_type = 'Paintings'
        node_value = str(tracker.get_slot("current_painting"))

        print("RequestAspect :: Node Type: " + node_type + " :: Node_value: " + str(node_value)) ##
        intent = tracker.latest_message['intent']
        print("RequestAspect :: Intent: " + str(intent['name'])) ##
        global init_setting
        if intent['name'] == 'request_person':
            subject = 'Person'
            init_setting = 2
        elif intent['name'] == 'request_movement':
            subject = 'Movement'
            init_setting = 2
        elif intent['name'] == 'request_collection':
            subject = 'Collection'
            init_setting = 2
        elif intent['name'] == 'request_material':
            subject = 'Material'
            init_setting = 3
        elif intent['name'] == 'request_keyword':
            subject = 'Keyword'
            init_setting = 3
        elif intent['name'] == 'request_genre':
            subject = 'Genre'
            init_setting = 3
        elif intent['name'] == 'request_exhibition':
            subject = 'Exhibition'
            init_setting = 2
        elif intent['name'] == 'request_country':
            subject = 'Country'
            init_setting = 1
        elif intent['name'] == 'request_city':
            subject = 'City'
            init_setting = 1
        elif intent['name'] == 'request_date':
            subject = 'date'
            init_setting = 1
        else:
            query = GenerateQuery.get_node_information_query(node_value, node_type)
            graph_response = GenerateQuery.connect_to_kg(query)
            
            if graph_response != []:
                dispatcher.utter_message(str(graph_response[0]['a']['exhibit']))
                print("RequestAspect :: Graph Response: " + str(graph_response[0]['a']['exhibit'])) ##
                ## add property in has_VISITED link about interest in description ##
                link_query = GenerateQuery.add_link_property_query(guest_id, node_value, interest= "description")
                GenerateQuery.connect_to_kg(link_query)
                init_setting = 1

            else:
                dispatcher.utter_message(text="Data not found")
                print("RequestAspect :: Graph Response: Data not found") ##
            return []

        query = GenerateQuery.get_aspect_information_query(node_value, node_type, subject)
        graph_response = GenerateQuery.connect_to_kg(query)
        global latest_aspect
        latest_aspect = subject
        if graph_response != []:
            print(graph_response)
            if subject == 'date':
                dispatcher.utter_message(str(graph_response[0]['a["date"]'])) ## PRESENT DATE DIFFERENTLY ##
                print("RequestAspect :: Graph Response: " + str(graph_response[0]['a["date"]'])) ##
                ## add property in has_VISITED link about interest in date ##
                link_query = GenerateQuery.add_link_property_query(guest_id, node_value, interest= "date")
                GenerateQuery.connect_to_kg(link_query)

            else: 
                
                dispatcher.utter_message(str(graph_response[0]['b']['name']))
                print("RequestAspect :: Graph Response: " + str(graph_response[0]['b']['name'])) ##
                link_query = GenerateQuery.make_connection_query(guest_id, graph_response[0]['b']['name'], "has_ASKED")
                GenerateQuery.connect_to_kg(link_query)
                ## ADD LOGIC TO CHECK IF THIS LINK ALREADY EXISTS AND INCREASE TALLY IF YES ##
                


        else:
            dispatcher.utter_message(text="Sorry I could not find anything about what you were asking for. I can help "
                                          "you with by telling you the paintings, painter, exhibition, genre, "
                                          "country, city, date, collection,etc")
            print("RequestAspect :: Graph Response: Data not found") ##

        print("RequestAspect::InitSetting: " + str(init_setting))
        return []


class RequestTopic(Action):
    def name(self):
        return "action_request_topic"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        print("RequestTopic :: Executed.")
        entities = tracker.latest_message['entities']
        node_value = ''
        node_type = ''

        for ent in entities:
            node_value = ent['value']
            node_type = ent['entity']
        
        print("RequestTopic :: Node Type: " + str(node_type) + " :: Node Value: " + str(node_value)) ##
        if node_value and node_type:
            if node_type == 'Paintings':
                query = GenerateQuery.get_node_information_query(node_value, node_type)
                graph_response = GenerateQuery.connect_to_kg(query)
                if graph_response != []:
                    dispatcher.utter_message(str(graph_response[0]['a']['exhibit']))     
                    print("RequestTopic :: Graph Response - Painting: " + str(graph_response[0]['a']['exhibit'])) ##
                    
                else:
                    dispatcher.utter_message(text="Data not found")
                    print("RequestTopic :: Graph Response - Painting: Data not found.") ##
                return []
            else:
                query = GenerateQuery.get_node_information_query(node_value, node_type)
                graph_response = GenerateQuery.connect_to_kg(query)
                if graph_response != []:
                    dispatcher.utter_message(str(graph_response[0]['a']['description']))
                    print("RequestTopic :: Graph Response - Aspects: " + str(graph_response[0]['a']['description'])) ##

                else:
                    dispatcher.utter_message(text="Data not found")
                    print("RequestTopic :: Graph Response - Aspects: Data not found.") ##


                return []

class Storeinterest(Action): ## This function adds interest value of 1 to a certain link if the user expresses interest ##
    def name(self):
        return "action_store_interest"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        node_value = str(tracker.get_slot("current_painting"))
        print("Storeinterest :: Current painting: " + node_value) ##
        print("Storeinterest :: latest_aspect: " + latest_aspect) ##
        link_query = GenerateQuery.add_link_property_query(guest_id, node_value, latest_aspect, 1)
        GenerateQuery.connect_to_kg(link_query)
        print("ActionStoreInterest::Executed")
        return []

class BotTurn(Action):
    def name(self):
        return "action_bot_turn"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        global init_setting
        if init_setting == 0:
            dispatcher.utter_message(text="Do you want to know about anything else?")
        elif init_setting == 1:
            dispatcher.utter_message(text="Are you interested to know about attribute 1 or attribute 2?") 
            # need code to randomly select attributes which have not been asked yet
        elif init_setting == 2:
            dispatcher.utter_message(text="Would you like to know more about this or something else?")
            #also fetch the one other attribute randomly from those not selected before


        elif init_setting == 3:
            dispatcher.utter_message(text="Would you like to know more about this or something else?")
            
            # in response the user will make some choices which need to be detected through intents, and will need appropriate actions based on their choice
            # for setting 0, the current actions can handle it
            # for setting 1, need to understand answer and use it to feed into existing actions. also understand none and both repsonses.
            # for setting 2, need to understand more and choice of a differnet attribute. or both. or none. 
            # based on choice, make connections in the neo4j and adjust interest

        return[]

# class random_interested_attributes(Action):
#     def name(self):
#         return "action_random_interested_attributes"
#     def run(self, dispatcher: CollectingDispatcher,
#             tracker: Tracker,
#             domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
#         return[]

# class random_2_choices(Action):
#     def name(self):
#         return "action_random_2_choice"
#     def run(self, dispatcher: CollectingDispatcher,
#             tracker: Tracker,
#             domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
#         intent1,intent2=1,0

#         # Set multiple slots
#         return [
#             SlotSet("intent1", intent1),
#             SlotSet("intent2", intent2)
#         ]
#         return[]

# class request_both(Action):
#     def name(self):
#         return "action_request_both"
#     def run(self, dispatcher: CollectingDispatcher,
#             tracker: Tracker,
#             domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
#         slot_value1 = tracker.get_slot("intent1")
#         slot_value2 = tracker.get_slot("intent2")
#         functions.request_aspect(slot_value1)
#         functions.request_aspect(slot_value2)

#         #function to store interest in both
#         return[]

# class choose_none(Action):
#     def name(self):
#         return "action_choose_none"
#     def run(self, dispatcher: CollectingDispatcher,
#             tracker: Tracker,
#             domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
#         slot_value1 = str(tracker.get_slot("intent1"))
#         slot_value2 = str(tracker.get_slot("intent2"))
#         #function to store interest in both
#         return[]

# class Register_interest(Action):

#     def name(self):
#         return "action_register_interest"

#     def run(self, dispatcher: CollectingDispatcher,
#             tracker: Tracker,
#             domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
#         intent = tracker.latest_message['intent']
#         #function to store interest in KG
#         return[]

# class Request_description(Action):

#     def name(self):
#         return "action_request_description"

#     def run(self, dispatcher: CollectingDispatcher,
#             tracker: Tracker,
#             domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
#         intent = tracker.latest_message['intent']
#         #function to store interest in KG
#         return[]

# class functions():
#     @staticmethod
#     def request_aspect(self, intent1,dispatcher: CollectingDispatcher,tracker: Tracker,domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
#         node_type = 'Paintings'
#         node_value = str(tracker.get_slot("current_painting"))

#         intent=intent1

#         if intent['name'] == 'request_person':
#             subject = 'Person'
#         elif intent['name'] == 'request_movement':
#             subject = 'Movement'
#         elif intent['name'] == 'request_collection':
#             subject = 'Collection'
#         elif intent['name'] == 'request_material':
#             subject = 'Material'
#         elif intent['name'] == 'request_keyword':
#             subject = 'Keyword'
#         elif intent['name'] == 'request_genre':
#             subject = 'Genre'
#         elif intent['name'] == 'request_exhibition':
#             subject = 'Exhibition'
#         elif intent['name'] == 'request_country':
#             subject = 'Country'
#         elif intent['name'] == 'request_city':
#             subject = 'City'
#         else:
#             dispatcher.utter_message(text="Data not found")
#             query = GenerateQuery.get_node_information_query(node_value, node_type)
#             graph_response = GenerateQuery.connect_to_kg(query)

#             if graph_response != []:
#                 dispatcher.utter_message(str(graph_response[0]['a']['exhibit']))
#             else:
#                 dispatcher.utter_message(text="Data not found")
#             return []

#         query = GenerateQuery.get_aspect_information_query(node_value, node_type, subject)
#         graph_response = GenerateQuery.connect_to_kg(query)

#         if graph_response != []:
#             dispatcher.utter_message(str(graph_response[0]['b']['name']))

#         else:
#             dispatcher.utter_message(text="Sorry I could not find anything about what you were asking for. I can hep "
#                                           "you with by telling you the paintings, painter, exhibition, genre, "
#                                           "country, city, date, collection,etc")
#         dispatcher.utter_message(text=str(subject))

#         return []


class GenerateQuery:

    @staticmethod
    def connect_to_kg(query):
        graph = Graph(
            scheme="neo4j",
            host="localhost",
            port=7687,
            auth=("neo4j", "apca1234"))
        data = graph.run(str(query)).data()
        return data

    @staticmethod
    def get_node_information_query(node_name, node_type=None):
        query = "MATCH (a:" + node_type + "{name: \"" + node_name + "\"}) Return a"
        return query

    @staticmethod
    def get_painting_query(name_painting):
        # url="url"
        query = "MATCH (a:Paintings{name: \"" + name_painting + "\"}) Return a.uri"
        return query
    
    @staticmethod
    def get_node_property_information_query(node_name, node_type=None, property=None):
        query = "MATCH (a:" + node_type + "{name: \""+node_name+"\"}) Return a[\""+property+"\"]"
        return query

    @staticmethod
    def get_aspect_information_query(node_name, node_type_1=None, node_type_2 =None):
        if node_type_2 == 'date':
            query = "MATCH (a:" + node_type_1 + "{name: \""+node_name+"\"}) Return a[\""+node_type_2+"\"]"
        else:
            query = "MATCH (a:" + node_type_1 + "{name: \""+node_name+"\"})--(b:"+node_type_2+") Return b"
        return query

    @staticmethod
    def create_new_guest_query(guestname, guesttime):
        query = "CREATE (g:GUEST {id: \""+ guest_id + "\", name: \"" + guestname + "\", date: \"" + str(guesttime.date()) + "\", time: \"" + str(guesttime.time()) + "\"})"
        return query
    
    @staticmethod
    def make_connection_query(guest_id, kg_value, relation):
        if isinstance(kg_value, str):
            query = "MATCH (start), (end) WHERE start.id = \""+guest_id+"\" AND end.name = \""+str(kg_value)+"\" CREATE (start)-[r:"+relation+" {id: \""+str(guest_id)+str(datetime.now())+"\", date: 0, description: 0}]->(end)"
            print("GenerateQuery::MakeConnectionQuery: \n" + query)
        elif isinstance(kg_value, int):
            query = "MATCH (start), (end) WHERE start.id = \""+guest_id+"\" AND end.id = \""+str(kg_value)+"\" CREATE (start)-[r:"+relation+" {id: \""+str(guest_id)+str(datetime.now())+"\", interest: 0}]->(end)"
            print("GenerateQuery::MakeConnectionQuery: \n" + query)

        return query
    
    @staticmethod
    def add_link_property_query(guest_id, kg_value, label = "None", interest = "None"):
        if label == "description":
            query = "MATCH (start)-[r]->(end) WHERE start.id = \"" + guest_id + "\" AND end.name = \"" + kg_value + "\"SET r.description= \"1\""
        elif label == "date":
            query = "MATCH (start)-[r]->(end) WHERE start.id = \"" + guest_id + "\" AND end.name = \"" + kg_value + "\"SET r.date= \"1\""
        else:
            query = "MATCH (guest)-[r:has_VISITED]->(painting)-[q]->(end) WHERE guest.id = \"" + guest_id + "\" AND painting.name = \"" + kg_value + "\" AND end:" + label + " match (guest)-[p]->(end) SET p.interest= \"1\""
        
        print("GenerateQuery::AddLinkProperty: " + query)
        return query

    @staticmethod
    def find_linked_labels_query(painting_name):
        query = (
        "MATCH (p:Paintings {name: \"" + painting_name + "\"})-[r]-(linked_node) "
        "RETURN DISTINCT labels(linked_node) AS linked_labels"
    )
    print("GenerateQuery::FindLinkedLabels: " + query)
    return query
