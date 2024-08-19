
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
import helper
from kg import GenerateQuery
import requests

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
painting_linked_labels = helper.get_painting_links()
# print(painting_linked_labels)

# Dictionary to store Guest's likes and dislikes
guest_interest = {'Likes':[], 'Dislikes':[]}

# variable to keep track of the bot's turn each painting
first_turn = 0

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
         create_guest = GenerateQuery.create_new_guest_query(guest_id, guestname, guesttime)
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
        # print("ActionNextPainting::Intent = " + intent['name']) ##
        painting_number = tracker.get_slot("painting_number")
        global flag_finish_tour, first_turn, guest_id, guest_interest, painting_linked_labels
        if painting_number == 16: flag_finish_tour = True
        if painting_number == None: painting_number = 0
        print("ActionNextPainting::Intent = " + intent['name']) ##
        print("ActionNextPainting::current painting id slot = " + str(painting_number)) ##
        p = False
        painting_name = tracker.get_slot("current_painting")

        if intent['name'] == 'affirmative' and painting_number == 0:
            p = True
        if p == True or intent['name'] == 'request_next_painting':
            p == False
            # reset the bot's turn when next painting comes
            if first_turn > 0: first_turn = 0

            #restart the conversation if all paintings have been viewed
            if flag_finish_tour == True:
                dispatcher.utter_message(text="We have come to the end of the tour. I hope you enjoyed it. Come back again soon.")
                flag_finish_tour = False
                return[Restarted()]
            
            current = paintings[painting_number]
            sep = ". "
            print("ActionNextPainting::Current Painting = " + current)
            
            query = GenerateQuery.make_connection_query(guest_id, current,"has_VISITED")
            GenerateQuery.connect_to_kg(query)
            # SlotSet("current_painting", current)
            add = [] # list of additional responses to add to the introduction
            #if it is the first painting
            if painting_number == 0:
                dispatcher.utter_message(response = "utter_painting_one_description", current_painting = current)
            # if it is the last painting
            elif painting_number == 15:
                dispatcher.utter_message(text = "We have arrived at the final painting of this exhibition.")
                dispatcher.utter_message(response = "utter_paintings_description", current_painting = current)
                chosen_labels = helper.choose_rand_desc(helper.get_guest_links(guest_id), guest_id, guest_interest, painting_linked_labels, current)
                if len(chosen_labels) != 0:
                    for i in range(len(chosen_labels)):
                        if chosen_labels[i] in painting_linked_labels[current]:
                            helper.remove_attribute_for_painting(painting_linked_labels, current, chosen_labels[i])
                            query1 = GenerateQuery.get_aspect_information_query(current, "Paintings", chosen_labels[i])
                            graph_response1 = GenerateQuery.connect_to_kg(query1)
                            temp = "The " + str(chosen_labels[i]) + "of this painting is " + str(graph_response1[0]['b']['name'])
                            add.append(temp)
                    res = sep.join(add)
                    print("NextPainting::AdditionalInfo: ", res)
                    dispatcher.utter_message(text = res)
            # for the rest of the paintings
            else:
                dispatcher.utter_message(response = "utter_paintings_description", current_painting = current)
                chosen_labels = helper.choose_rand_desc(helper.get_guest_links(guest_id), guest_id, guest_interest, painting_linked_labels, current)
                print("NewPainting::ChosenLabels: ", chosen_labels) ##
                if len(chosen_labels) != 0:
                    for i in range(len(chosen_labels)):
                        if chosen_labels[i] in painting_linked_labels[current]:
                            helper.remove_attribute_for_painting(painting_linked_labels, current, chosen_labels[i])
                            query1 = GenerateQuery.get_aspect_information_query(current, "Paintings", chosen_labels[i])
                            graph_response1 = GenerateQuery.connect_to_kg(query1)
                            temp = "The " + str(chosen_labels[i]) + " of this painting is " + str(graph_response1[0]['b']['name'])
                            add.append(temp)
                            
                    res = sep.join(add)
                    print("NextPainting::AdditionalInfo: ", res)
                    dispatcher.utter_message(text = res)
                

            # if intent['name'] == 'request_next_painting':return [SlotSet("current_painting",current), SlotSet("painting_number", painting_number+1)]
            # slot_value = tracker.get_slot("current_painting")
            # url = "http://127.0.0.1:5001/set_painting"
            # data = {"slot_value": slot_value}
            # response = requests.post(url, data=data)
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
        global init_setting, first_turn
        if intent['name'] == 'request_person':
            subject = 'Person'
            if first_turn < 2: init_setting = 2            
        elif intent['name'] == 'request_movement':
            subject = 'Movement'
            if first_turn < 2: init_setting = 2
        elif intent['name'] == 'request_collection':
            subject = 'Collection'
            if first_turn < 2: init_setting = 2
        elif intent['name'] == 'request_material':
            subject = 'Material'
            if first_turn < 2: init_setting = 3
        elif intent['name'] == 'request_keyword':
            subject = 'Keyword'
            if first_turn < 2: init_setting = 3
        elif intent['name'] == 'request_genre':
            subject = 'Genre'
            if first_turn < 2: init_setting = 3
        elif intent['name'] == 'request_exhibition':
            subject = 'Exhibition'
            if first_turn < 2: init_setting = 2
        elif intent['name'] == 'request_country':
            subject = 'Country'
            if first_turn < 2: init_setting = 1
        elif intent['name'] == 'request_city':
            subject = 'City'
            if first_turn < 2: init_setting = 1
        elif intent['name'] == 'request_date':
            subject = 'date'
            if first_turn < 2: init_setting = 1
        else:
            query = GenerateQuery.get_node_information_query(node_value, node_type)
            graph_response = GenerateQuery.connect_to_kg(query)
            helper.remove_attribute_for_painting(painting_linked_labels, node_value, "description")
            if graph_response != []:
                dispatcher.utter_message(str(graph_response[0]['a']['exhibit']))
                print("RequestAspect :: Graph Response: " + str(graph_response[0]['a']['exhibit'])) ##
                ## add property in has_VISITED link about interest in description ##
                link_query = GenerateQuery.add_link_property_query(guest_id, node_value, label="description", interest = 1)
                GenerateQuery.connect_to_kg(link_query)
                if first_turn < 2: init_setting = 1
                

            else:
                dispatcher.utter_message(text="Sorry I could not find anything about what you were asking for. I can help "
                                          "you with by telling you the paintings, painter, exhibition, genre, "
                                          "country, city, date, collection,etc")
                print("RequestAspect :: Graph Response: Data not found") ##
            return []

        query = GenerateQuery.get_aspect_information_query(node_value, node_type, subject)
        graph_response = GenerateQuery.connect_to_kg(query)
        global latest_aspect
        latest_aspect = subject
        helper.remove_attribute_for_painting(painting_linked_labels, node_value, subject)
        print("PaintLinks::UpdatedDict :") ##
        print(painting_linked_labels) ##
        if graph_response != []:
            print(graph_response)
            if subject == 'date':
                response = str(graph_response[0]['a["date"]'])
                datetime_object = datetime.strptime(response, "%Y-%m-%dT%H:%M:%S")
                year = datetime_object.year
                date = "This painting is from " + str(year)
                dispatcher.utter_message(text = date) ## PRESENT DATE DIFFERENTLY ##
                print("RequestAspect :: Graph Response: " + str(year)) ##
                ## adds property in has_VISITED link about interest in date ##
                link_query = GenerateQuery.add_link_property_query(guest_id, node_value, label = "date", interest = 1)
                GenerateQuery.connect_to_kg(link_query)                

            else: 
                if subject == 'Person': 
                    reply =  str(graph_response[0]['b']['name']) + " created this painting. He was a " + str(graph_response[0]['b']['description'])
                elif subject == 'Movement':
                    reply =  str(graph_response[0]['b']['name']) + " which was a " + str(graph_response[0]['b']['description'])
                elif subject == 'Collection':
                    reply =  str(graph_response[0]['b']['name']) + ", " + str(graph_response[0]['b']['description'])
                elif subject == 'Exhibition':
                    reply =  str(graph_response[0]['b']['name']) + ", " + str(graph_response[0]['b']['description'])
                else:
                    reply = "The " + str(subject) + " of this painting is " + str(graph_response[0]['b']['name'])
                dispatcher.utter_message(reply)
                print("RequestAspect :: Graph Response: " + reply) ##
                link_query = GenerateQuery.make_connection_query(guest_id, graph_response[0]['b']['name'], "has_ASKED")
                GenerateQuery.connect_to_kg(link_query)
                ## ADD LOGIC TO CHECK IF THIS LINK ALREADY EXISTS AND INCREASE TALLY IF YES ##
                
        else:
            dispatcher.utter_message(text="Sorry I could not find anything about what you were asking for. I can help "
                                          "you with by telling you the paintings, painter, exhibition, genre, "
                                          "country, city, date, collection,etc")
            print("RequestAspect :: Graph Response: Data not found") ##

        print("RequestAspect::InitSetting: " + str(init_setting))
        if not first_turn < 2: init_setting = 0
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
        
        intent = tracker.latest_message['intent']
        print("StoreInterest :: Intent: " + str(intent['name'])) ##
        node_value = str(tracker.get_slot("current_painting"))
        print("Storeinterest :: Current painting: " + node_value) ##
        print("Storeinterest :: latest_aspect: " + latest_aspect) ##
        if intent['name'] == "shows_interest_pos":
            link_query = GenerateQuery.add_link_property_query(guest_id, node_value, latest_aspect, interest = 1)
            GenerateQuery.connect_to_kg(link_query)
            # adds this aspect to guest's liked list
            guest_interest["Likes"].append(latest_aspect)
            dispatcher.utter_message(text = "Oh that's good to know. I'll try to remember that!")
        elif intent['name'] == "shows_interest_neg":
            link_query = GenerateQuery.add_link_property_query(guest_id, node_value, latest_aspect, interest = -1)
            GenerateQuery.connect_to_kg(link_query)
            # adds this aspect to guest's liked list
            guest_interest["Dislikes"].append(latest_aspect)
            dispatcher.utter_message(text = "Yikes, okay I will try to remember that!")

        print("ActionStoreInterest::Executed")
        print(guest_interest)
        return []

class BotTurn(Action):
    def name(self):
        return "action_bot_turn"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        painting_name = tracker.get_slot("current_painting")
        global init_setting, first_turn
        
        if init_setting == 0:
            print("BotTurn::InitSetting_0::Success : bot turn = ", first_turn)
            dispatcher.utter_message(text="Let me know if you want to know about anything else. You can also move to the next painting.")
            first_turn = first_turn + 1
        elif init_setting == 1 or init_setting == 2:
            if first_turn < 2:
                print("BotTurn::InitSetting_1_2::Success : bot turn = ", first_turn) ##
                first_turn = first_turn + 1
                rand_label_1 = helper.choose_rand_label(painting_linked_labels, painting_name, guest_interest, guest_id)
                rand_label_2 = helper.choose_rand_label(painting_linked_labels, painting_name, guest_interest, guest_id)
                ques = "What would you like to know about next: " + str(rand_label_1) + " or " + str(rand_label_2) + "?"
                if rand_label_1 in guest_interest['Likes']:
                    ques = "I remember you liked knowing about " + str(rand_label_1) + ". Do you want to know about it again?"
                elif rand_label_2 in guest_interest['Likes']:
                    ques = "I remember you liked knowing about " + str(rand_label_2) + ". Do you want to know about it again?"
                dispatcher.utter_message(text = ques)                
            else: print("BotTurn::InitSetting_1_2::Failed : bot turn = ", first_turn) ##
        elif init_setting == 3:
            if first_turn < 2:
                print("BotTurn::InitSetting_3::Success : bot turn = ", first_turn) ##
                first_turn = first_turn + 1
                rand_label = helper.choose_rand_label(painting_linked_labels, painting_name, guest_interest, guest_id)
                ques = "Would you like to know more about this or something else like the " + str(rand_label) + "?"
                dispatcher.utter_message(text = ques)
            else: print("BotTurn::InitSetting_3::Failed : bot turn = ", first_turn) ##

            # in response the user will make some choices which need to be detected through intents, and will need appropriate actions based on their choice
            # for setting 0, the current actions can handle it
            # for setting 1, need to understand answer and use it to feed into existing actions. also understand none and both repsonses.
            # for setting 2, need to understand more and choice of a differnet attribute. or both. or none. 
            # based on choice, make connections in the neo4j and adjust interest

        return[]

class MoreInfo(Action):
    def name(self):
        return "action_more_info"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        global latest_aspect, painting_linked_labels, guest_interest, guest_id, init_setting
        node_type = 'Paintings'
        node_value = str(tracker.get_slot("current_painting"))
        query = GenerateQuery.get_aspect_information_query(node_value, node_type, latest_aspect)
        graph_response = GenerateQuery.connect_to_kg(query)
        reply = "Some details about " + str(latest_aspect) + ": " + str(graph_response[0]['b']['description'])
        
        print("MoreInfo::CypherQuery: ", query) ##
        print("MoreInfo::Description: ", reply) ##
        dispatcher.utter_message(text = reply)
        init_setting = 0
        
        # query_1 = GenerateQuery.get_node_property_information_query(reply, latest_aspect, 'description')
        # graph_response_1 = GenerateQuery.connect_to_kg(query_1)
        # print("MoreInfo::CypherQuery: ", query_1) ##
        # print("MoreInfo::Description: ",graph_response_1) ##


        return

class WhatElse(Action):
    def name(self):
        return "action_what_else"

    def run(self, dispatcher: CollectingDispatcher,
            tracker: Tracker,
            domain: Dict[Text, Any]) -> List[Dict[Text, Any]]:
        
        global latest_aspect, painting_linked_labels, guest_interest, guest_id, init_setting
        # node_type = 'Paintings'
        node_value = str(tracker.get_slot("current_painting"))
        whatelse = painting_linked_labels[node_value]
        res = "For this painting, you can ask me about the following " + str(whatelse)
        dispatcher.utter_message(text= res)
    
        return