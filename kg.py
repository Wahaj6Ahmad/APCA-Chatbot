from datetime import datetime
from py2neo import Node, Relationship, Graph

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
    def create_new_guest_query(guest_id, guestname, guesttime):
        query = "CREATE (g:GUEST {id: \""+ guest_id + "\", name: \"" + guestname + "\", date: \"" + str(guesttime.date()) + "\", time: \"" + str(guesttime.time()) + "\"})"
        return query
    
    # @staticmethod
    # def make_connection_query(guest_id, kg_value, relation):
    #     if isinstance(kg_value, str):
    #         query = "MATCH (start), (end) WHERE start.id = \""+guest_id+"\" AND end.name = \""+str(kg_value)+"\" CREATE (start)-[r:"+relation+" {id: \""+str(guest_id)+str(datetime.now())+"\", date: 0, description: 0}]->(end)"
    #         print("GenerateQuery::MakeConnectionQuery: \n" + query)
    #     elif isinstance(kg_value, int):
    #         query = "MATCH (start), (end) WHERE start.id = \""+guest_id+"\" AND end.id = \""+str(kg_value)+"\" CREATE (start)-[r:"+relation+" {id: \""+str(guest_id)+str(datetime.now())+"\", interest: 0}]->(end)"
    #         print("GenerateQuery::MakeConnectionQuery: \n" + query)

    #     return query
    @staticmethod
    def make_connection_query(guest_id, kg_value, relation):
        if relation == "has_VISITED":
            query = "MATCH (start), (end) WHERE start.id = \""+guest_id+"\" AND end.name = \""+str(kg_value)+"\" CREATE (start)-[r:"+relation+" {id: \""+str(guest_id)+str(datetime.now())+"\", date: 0, description: 0}]->(end)"
            print("GenerateQuery::MakeConnectionQuery: \n" + query)
        elif relation == "has_ASKED":
            query = "MATCH (start), (end) WHERE start.id = \""+guest_id+"\" AND end.name = \""+str(kg_value)+"\" CREATE (start)-[r:"+relation+" {id: \""+str(guest_id)+str(datetime.now())+"\", interest: 0}]->(end)"
            print("GenerateQuery::MakeConnectionQuery: \n" + query)

        return query
    
    @staticmethod
    def add_link_property_query(guest_id, kg_value, label = "None", interest=0):
        interest = str(interest)
        if label == "description":
            query = "MATCH (start)-[r]->(end) WHERE start.id = \"" + guest_id + "\" AND end.name = \"" + kg_value + "\"SET r.description= \"" + interest + "\""
        elif label == "date":
            query = "MATCH (start)-[r]->(end) WHERE start.id = \"" + guest_id + "\" AND end.name = \"" + kg_value + "\"SET r.date= \"" + interest + "\""
        else:
            query = "MATCH (guest)-[r:has_VISITED]->(painting)-[q]->(end) WHERE guest.id = \"" + guest_id + "\" AND painting.name = \"" + kg_value + "\" AND end:" + label + " match (guest)-[p]->(end) SET p.interest= \"" + interest + "\""
        
        print("GenerateQuery::AddLinkProperty: " + query)
        return query