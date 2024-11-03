import os
import pandas as pd
import re
import requests
import sqlite3
import json
import csv
from rdflib import Graph, URIRef, Literal, Namespace
from pandas import read_csv
from rdflib.namespace import RDF
from sparql_dataframe import get
from pandas import concat
from rdflib.plugins.stores.sparqlstore import SPARQLUpdateStore
from typing import List, Union, Optional

# To search for a file anywhere on the system
def find_file(filename, search_path="/"):  # start search from the system root
    for root, dirs, files in os.walk(search_path):
        if filename in files:
            return os.path.join(root, filename)
    return None

BLAZEGRAPH_ENDPOINT = 'http://127.0.0.1:9999/blazegraph/sparql'
CSV_FILEPATH = 'data/meta.csv'

class IdentifiableEntity(object): #Rubens
    def __init__(self, id: str):
        self.id = id

    def getId(self) -> str:
        return self.id


class Person(IdentifiableEntity):  # Rubens
    def __init__(self, id: str, name: str):
        self.name = name
        super().__init__(id)

    def getName(self) -> str:
        return self.name


class CulturalHeritageObject(IdentifiableEntity):  # Ben
    def __init__(
        self,
        id: str,
        title: str,
        date: Optional[str],
        owner: str,
        place: str,
        hasAuthor: Union[Person, List[Person], None] = None,
        author_id: Optional[str] = None,
        author_name: Optional[str] = None,
    ):
        super().__init__(str(id))
        self.id = id
        self.title = title
        self.date = date
        self.hasAuthor = hasAuthor or []
        self.owner = str(owner)
        self.place = place
        self.author_id = author_id
        self.author_name = author_name

        if type(hasAuthor) == Person:
            self.hasAuthor.append(Person)
        elif type(hasAuthor) == list:
            self.hasAuthor = hasAuthor

    def getTitle(self) -> str:
        return self.title

    def getOwner(self) -> str:
        return self.owner

    def getPlace(self) -> str:
        return self.place

    def getDate(self) -> Optional[str]:
        if self.date:
            return self.date
        return None

    def getAuthors(self) -> List[Person]:
        return self.hasAuthor


class NauticalChart(CulturalHeritageObject):
    pass


class ManuscriptPlate(CulturalHeritageObject):
    pass


class ManuscriptVolume(CulturalHeritageObject):
    pass


class PrintedVolume(CulturalHeritageObject):
    pass


class PrintedMaterial(CulturalHeritageObject):
    pass


class Herbarium(CulturalHeritageObject):
    pass


class Specimen(CulturalHeritageObject):
    pass


class Painting(CulturalHeritageObject):
    pass


class Model(CulturalHeritageObject):
    pass


class Map(CulturalHeritageObject):
    pass


class Activity(object):  # Rubens
    def __init__(
        self,
        refersTo: CulturalHeritageObject,
        institute: str,
        person: Optional[str],
        tool: Union[str, List[str], None],
        start: Optional[str],
        end: Union[str, List[str], None],
    ):
        self.refersTo = refersTo
        self.institute = institute
        self.person = person
        self.tool = []
        self.start = start
        self.end = end

        if type(tool) == str:
            self.tool.append(tool)
        elif type(tool) == list:
            self.tool = tool

    def getResponsibleInstitute(self) -> str:
        return self.institute

    def getResponsiblePerson(self) -> Optional[str]:
        if self.person:
            return self.person
        return None

    def getTools(self) -> set:
        return self.tool

    def getStartDate(self) -> Optional[str]:
        if self.start:
            return self.start
        return None

    def getEndDate(self) -> Optional[str]:
        if self.end:
            return self.end
        return None

    def refersTo(self) -> CulturalHeritageObject:
        return self.refersTo


class Acquisition(Activity):
    def __init__(
        self,
        refersTo: CulturalHeritageObject,
        institute: str,
        technique: str,
        person: Optional[str],
        start: Optional[str],
        end: Optional[str],
        tool: Union[str, List[str], None],
    ):
        super().__init__(refersTo, institute, person, tool, start, end)
        self.technique = technique

    def getTechnique(self) -> str:
        return self.technique


class Processing(Activity):
    pass


class Modelling(Activity):
    pass


class Optimising(Activity):
    pass


class Exporting(Activity):
    pass


class Handler(object):  # Ekaterina
    def __init__(self):
        self.dbPathOrUrl = ""

    def getDbPathOrUrl(self) -> str:
        return self.dbPathOrUrl

    def setDbPathOrUrl(self, pathOrUrl: str) -> bool:
        self.dbPathOrUrl = pathOrUrl
        return self.dbPathOrUrl == pathOrUrl


class UploadHandler(Handler):  # Ekaterina
    def __init__(self):
        super().__init__()

    def pushDataToDb(self, file_path: str) -> bool:
        # If the file is not found at the provided path, search for it
        if not os.path.isfile(file_path):
            file_name = os.path.basename(file_path)  # Extract file name from the path
            file_path = find_file(file_name)  # Search the entire system for the file

        if not file_path:
            raise FileNotFoundError(f"File '{file_name}' not found.")

        self.file_path = file_path
        blazegraph_endpoint = "http://127.0.0.1:9999/blazegraph/sparql"

        # Split file path for file extension
        _, extension = os.path.splitext(file_path)

        if extension == ".db":
            return self.upload_to_sqlite(file_path)

        elif extension == ".json":
            return self.upload_json_to_sqlite(file_path)

        elif extension == ".csv":
            return self.upload_csv_to_blazegraph(file_path, blazegraph_endpoint)

        else:
            raise Exception("Only .json, .csv, or .db files can be uploaded!")

    def upload_to_sqlite(self, file_path: str) -> bool:
        # Implement logic for uploading data to SQLite database
        with sqlite3.connect(self.dbPathOrUrl) as conn:
            df = pd.read_json(file_path)
            df.to_sql('process', conn, if_exists='replace')
        print("Uploaded data to SQLite database successfully.")
        return True

    def upload_json_to_sqlite(self, file_path: str) -> bool:
        # Implement logic for processing JSON data and uploading to SQLite
        with open(file_path, 'r') as file:
            data = json.load(file)

        with sqlite3.connect(self.dbPathOrUrl) as conn:
            for record in data:
                for table, rows in record.items():
                    if isinstance(rows, list):
                        pd.DataFrame(rows).to_sql(table, conn, if_exists='replace')
        print("Uploaded JSON data to SQLite database successfully.")
        return True

    def upload_csv_to_blazegraph(self, file_path: str, sparql_endpoint: str) -> bool:
        # Implement logic for processing CSV data and uploading RDF to Blazegraph
        graph = Graph()
        self.csv_to_rdf(file_path, graph)

        local_turtle_file = "output_triples.ttl"
        graph.serialize(destination=local_turtle_file, format="turtle")

        return self.upload_to_blazegraph(local_turtle_file, sparql_endpoint)

    def csv_to_rdf(self, file_path: str, graph: Graph):
        with open(file_path, 'r') as f:
            reader = csv.DictReader(f)
            namespace = Namespace("http://example.org/")
            
            for row in reader:
                subject = URIRef(namespace[row["Id"]])
                for key, value in row.items():
                    predicate = URIRef(namespace[key])
                    obj = Literal(value)
                    graph.add((subject, predicate, obj))

    def upload_to_blazegraph(self, turtle_file: str, sparql_endpoint: str) -> bool:
        headers = {'Content-Type': 'application/x-turtle'}

        with open(turtle_file, 'rb') as f:
            response = requests.post(sparql_endpoint, data=f, headers=headers)

        if response.status_code != 200:
            print(f"Upload failed: {response.status_code} - {response.reason}")
            print(f"Response text: {response.text}")
            return False 
        
        print("Upload to Blazegraph successful!")
        return True


class ProcessDataUploadHandler(UploadHandler):  # Ekaterina
    def __init__(self):
        super().__init__()
        self.file_path = find_file('process.json')
        self.db_file = "json.db"
        
        # Load the JSON file and set up the database
        self.load_json_and_setup_db()

    def load_json_and_setup_db(self):
        try:
            with open(self.file_path) as json_file:
                data = json.load(json_file)

            conn = sqlite3.connect(self.db_file)
            c = conn.cursor()

            # Create tables if they do not exist
            c.execute(
                """CREATE TABLE IF NOT EXISTS Acquisition (
                            object_id TEXT,
                            responsible_institute TEXT,
                            responsible_person TEXT,
                            technique TEXT,
                            tool TEXT,
                            start_date TEXT,
                            end_date TEXT
                        )"""
            )

            c.execute(
                """CREATE TABLE IF NOT EXISTS Processing (
                            object_id TEXT,
                            responsible_institute TEXT,
                            responsible_person TEXT,
                            tool TEXT,
                            start_date TEXT,
                            end_date TEXT
                        )"""
            )

            c.execute(
                """CREATE TABLE IF NOT EXISTS Modelling (
                            object_id TEXT,
                            responsible_institute TEXT,
                            responsible_person TEXT,
                            tool TEXT,
                            start_date TEXT,
                            end_date TEXT
                        )"""
            )

            c.execute(
                """CREATE TABLE IF NOT EXISTS Optimising (
                            object_id TEXT,
                            responsible_institute TEXT,
                            responsible_person TEXT,
                            tool TEXT,
                            start_date TEXT,
                            end_date TEXT
                        )"""
            )

            c.execute(
                """CREATE TABLE IF NOT EXISTS Exporting (
                            object_id TEXT,
                            responsible_institute TEXT,
                            responsible_person TEXT,
                            tool TEXT,
                            start_date TEXT,
                            end_date TEXT
                        )"""
            )

            for item in data:
                object_id = item["object id"]

                # Insert acquisition data
                acquisition = item.get("acquisition", {})
                c.execute(
                    """INSERT INTO Acquisition (object_id, responsible_institute, responsible_person, technique, tool, start_date, end_date)
                            VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (
                        object_id,
                        acquisition.get("responsible institute"),
                        acquisition.get("responsible person"),
                        acquisition.get("technique"),
                        ", ".join(acquisition.get("tool", [])) if acquisition.get("tool") else None,
                        acquisition.get("start date"),
                        acquisition.get("end date"),
                    ),
                )

                # Insert processing data
                processing = item.get("processing", {})
                c.execute(
                    """INSERT INTO Processing (object_id, responsible_institute, responsible_person, tool, start_date, end_date)
                            VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        object_id,
                        processing.get("responsible institute"),
                        processing.get("responsible person"),
                        ", ".join(processing.get("tool", [])) if processing.get("tool") else None,
                        processing.get("start date"),
                        processing.get("end date"),
                    ),
                )

                # Insert modelling data
                modelling = item.get("modelling", {})
                c.execute(
                    """INSERT INTO Modelling (object_id, responsible_institute, responsible_person, tool, start_date, end_date)
                            VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        object_id,
                        modelling.get("responsible institute"),
                        modelling.get("responsible person"),
                        ", ".join(modelling.get("tool", [])) if modelling.get("tool") else None,
                        modelling.get("start date"),
                        modelling.get("end date"),
                    ),
                )

                # Insert optimising data
                optimising = item.get("optimising", {})
                c.execute(
                    """INSERT INTO Optimising (object_id, responsible_institute, responsible_person, tool, start_date, end_date)
                            VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        object_id,
                        optimising.get("responsible institute"),
                        optimising.get("responsible person"),
                        ", ".join(optimising.get("tool", [])) if optimising.get("tool") else None,
                        optimising.get("start date"),
                        optimising.get("end date"),
                    ),
                )

                # Insert exporting data
                exporting = item.get("exporting", {})
                c.execute(
                    """INSERT INTO Exporting (object_id, responsible_institute, responsible_person, tool, start_date, end_date)
                            VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        object_id,
                        exporting.get("responsible institute"),
                        exporting.get("responsible person"),
                        ", ".join(exporting.get("tool", [])) if exporting.get("tool") else None,
                        exporting.get("start date"),
                        exporting.get("end date"),
                    ),
                )

            conn.commit()
            print("\nData insertion and querying completed successfully.")
        except FileNotFoundError:
            print("Error: JSON file not found.")
        except sqlite3.Error as e:
            print("\nSQLite error:", e)
        finally:
            if conn:
                conn.close()



class MetadataUploadHandler(UploadHandler):  # Ekaterina
    def __init__(self):
        super().__init__()
        self.my_graph = Graph()

        # Define resource classes
        self.NauticalChart = URIRef("https://schema.org/NauticalChart")
        self.ManuscriptPlate = URIRef("https://schema.org/ManuscriptPlate")
        self.ManuscriptVolume = URIRef("https://schema.org/ManuscriptVolume")
        self.PrintedVolume = URIRef("https://schema.org/PrintedVolume")
        self.PrintedMaterial = URIRef("https://schema.org/PrintedMaterial")
        self.Herbarium = URIRef("https://schema.org/Herbarium")
        self.Specimen = URIRef("https://schema.org/Specimen")
        self.Painting = URIRef("https://schema.org/Painting")
        self.Model = URIRef("https://schema.org/Model")
        self.Map = URIRef("https://schema.org/Map")
        self.Author = URIRef("https://schema.org/Author")

        # Define attributes
        self.title = URIRef("https://schema.org/name")
        self.date = URIRef("https://schema.org/dateCreated")
        self.owner = URIRef("https://schema.org/provider")
        self.place = URIRef("https://schema.org/contentLocation")
        self.identifier = URIRef("https://schema.org/identifier")
        self.label = URIRef("http://www.w3.org/2000/01/rdf-schema#label")
        self.hasAuthor = URIRef("https://schema.org/creator")

        # Base URL
        self.base_url = "https://github.com/katyakrsn/ds24project/"
        self.file_path_csv = "data/meta.csv"
        
        # Load heritage data from CSV
        self.heritage = pd.read_csv(
            find_file('meta.csv'),
            keep_default_na=False,
            dtype={
                "Id": "string",
                "Type": "string",
                "Title": "string",
                "Date": "string",
                "Author": "string",
                "Owner": "string",
                "Place": "string",
            },
        )

        # Process each row in the heritage DataFrame
        self.process_heritage_data()

    def process_heritage_data(self):
    # Process each row of heritage data and add RDF triples to the graph
        for idx, row in self.heritage.iterrows():
            class_uri = self.get_class_uri(row["Type"])
            resource_uri = URIRef(f"{self.base_url}{row['Id']}")

            # Handle missing date values
            row["Date"] = row["Date"].strip() if row["Date"].strip() else "Unknown"
            print(f"Missing Date at index {idx}" if row["Date"] == "Unknown" else "")
            
            # Handle missing and whitespace values
            date = row["Date"].strip() if row["Date"].strip() else "Unknown"
            title = row["Title"].strip() if row["Title"].strip() else "Unknown"
            owner = row["Owner"].strip() if row["Owner"].strip() else "Unknown"
            place = row["Place"].strip() if row["Place"].strip() else "Unknown"

            # Add triples to the graph
            self.my_graph.add((resource_uri, RDF.type, class_uri))
            self.my_graph.add((resource_uri, self.identifier, Literal(row["Id"])))
            self.my_graph.add((resource_uri, self.title, Literal(title)))
            self.my_graph.add((resource_uri, self.date, Literal(date)))
            self.my_graph.add((resource_uri, self.owner, Literal(owner)))
            self.my_graph.add((resource_uri, self.place, Literal(place)))

            # Handle Author
            author = row["Author"].strip() if row["Author"].strip() else "Unknown"
            if author != "Unknown":
                self.add_author_data(row, resource_uri, idx)
            else:
                print(f"Missing Author at index {idx}")
                self.add_author_data({"Author": "Unknown"}, resource_uri, idx)  # Add placeholder author

        # Serialize graph to a local file
        turtle_file_path = "output_triples.ttl"
        self.my_graph.serialize(destination=turtle_file_path, format="ttl")

        # Log the creation of the Turtle file
        print(f"Turtle file created at: {turtle_file_path}")
        with open(turtle_file_path, 'r') as f:
            print(f"Contents of the Turtle file:\n{f.read()[:500]}")  # Log first 500 characters

        # Upload triples to the Blazegraph database
        if not self.upload_to_blazegraph(turtle_file_path, "http://127.0.0.1:9999/blazegraph/sparql"):
            print("Failed to upload RDF to Blazegraph!")
            return


    def get_class_uri(self, type_value):
        # Return the URI of the class based on the type of CulturalHeritageObject
        class_mapping = {
            "Nautical chart": self.NauticalChart,
            "Manuscript plate": self.ManuscriptPlate,
            "Manuscript volume": self.ManuscriptVolume,
            "Printed volume": self.PrintedVolume,
            "Printed material": self.PrintedMaterial,
            "Herbarium": self.Herbarium,
            "Specimen": self.Specimen,
            "Painting": self.Painting,
            "Model": self.Model,
            "Map": self.Map,
        }
        return class_mapping.get(type_value, None)

    def add_author_data(self, row, resource_uri, idx):
        # Add author data to the RDF graph
        author = row["Author"]
        text_before_parentheses = author.split(" (")[0]
        authorID = re.findall(r"\((.*?)\)", author)
        authorID = authorID[0] if authorID else "noID"
        authorIRI = self.base_url + text_before_parentheses.replace(" ", "_").replace(",", "")

        self.my_graph.add((resource_uri, self.hasAuthor, URIRef(authorIRI)))
        self.my_graph.add((URIRef(authorIRI), self.identifier, Literal(authorID)))
        self.my_graph.add((URIRef(authorIRI), RDF.type, self.Author))
        self.my_graph.add((URIRef(authorIRI), self.label, Literal(text_before_parentheses)))

    def upload_to_blazegraph(self, turtle_file, sparql_endpoint):
        # Upload RDF triples to Blazegraph
        store = SPARQLUpdateStore()
        store.open((sparql_endpoint, sparql_endpoint))
        
        # Upload triples to the Blazegraph database
        try:
            for triple in self.my_graph.triples((None, None, None)):
                store.add(triple)
            store.close()
        except Exception as e:
            print(f"Error during upload to Blazegraph: {e}")
            store.close() 
            raise Exception("Failed to upload RDF to Blazegraph!")

        # Run a SPARQL query to confirm upload
        return self.run_sparql_query()

    def run_sparql_query(self):
        # Run a SPARQL query to confirm that data has been uploaded
        sparql_query = """
            SELECT ?subject ?predicate ?object
            WHERE {
                ?subject ?predicate ?object .
            }
            ORDER BY ASC(xsd:integer(REPLACE(str(?subject), "https://github.com/katyakrsn/ds24project/", "")))
        """
        sparql_endpoint = "http://127.0.0.1:9999/blazegraph/sparql"
        response = requests.post(sparql_endpoint, data={"query": sparql_query})
        
        if response.status_code != 200:
            print(f"Error during SPARQL query: {response.status_code} - {response.reason}")
            return False
        else:
            print("SPARQL query executed successfully.")
            print(f"Response: {response.text}")
            return True
                
class QueryHandler(Handler):
    def __init__(self):
        super().__init__()

    def getById(self, input_id: str) -> pd.DataFrame:  # Ekaterina/Rubens
        endpoint = self.blazegraph_endpoint
        id_author_query = f"""
        PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX schema: <https://schema.org/>

        SELECT ?identifier ?name ?title
        WHERE {{
            ?entity schema:identifier "{input_id}" .
            ?entity schema:creator ?Author .
            ?Author rdfs:label ?name .
            ?Author schema:identifier ?identifier .
            ?entity schema:name ?title
        }}
        """
        df_sparql = get(endpoint, id_author_query, True)
        return df_sparql

class MetadataQueryHandler(QueryHandler):
    def __init__(self):
        self.blazegraph_endpoint = BLAZEGRAPH_ENDPOINT
        self.csv_file_path = CSV_FILEPATH

    def getAllPeople(self) -> pd.DataFrame:  # Rubens
        sparql_query = """
        PREFIX schema: <https://schema.org/>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        
        SELECT ?id ?name
        WHERE {
            ?entity schema:creator ?Author .
            ?Author rdfs:label ?name .
            ?Author schema:identifier ?id .
        }
        """
        df_sparql = get(self.blazegraph_endpoint, sparql_query, True)
        return df_sparql

    def getAllCulturalHeritageObjects(self) -> pd.DataFrame:  # Ekaterina
        endpoint = self.blazegraph_endpoint
        cultural_object_query = """
        PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX schema: <https://schema.org/>

        SELECT (REPLACE(STR(?type), "https://schema.org/", "") AS ?type_name) ?id ?title ?date ?owner ?place ?author_id ?author_name
        WHERE {
        ?cultural_object rdf:type ?type .
        ?cultural_object schema:name ?title .
        OPTIONAL { ?cultural_object schema:identifier ?id }
        OPTIONAL { ?cultural_object schema:dateCreated ?date }
        OPTIONAL { ?cultural_object schema:provider ?owner }
        OPTIONAL { ?cultural_object schema:contentLocation ?place }
        OPTIONAL { ?cultural_object schema:creator ?author }
        OPTIONAL { ?author schema:identifier ?author_id }
        OPTIONAL { ?author rdfs:label ?author_name }
        
        FILTER(?type IN (
        <https://schema.org/NauticalChart>,
        <https://schema.org/ManuscriptPlate>,
        <https://schema.org/ManuscriptVolume>,
        <https://schema.org/PrintedVolume>,
        <https://schema.org/PrintedMaterial>,
        <https://schema.org/Herbarium>,
        <https://schema.org/Specimen>,
        <https://schema.org/Painting>,
        <https://schema.org/Model>,
        <https://schema.org/Map>
        ))
        FILTER(?author_name != "NaN")
        FILTER(?author_id != "NaN")
        }
        """
        df_sparql = get(endpoint, cultural_object_query, True)
        return df_sparql

    def getAuthorsOfCulturalHeritageObject(self, input_id) -> pd.DataFrame:  # Rubens
        endpoint = self.blazegraph_endpoint
        id_author_query = f"""
        PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX schema: <https://schema.org/>

        SELECT ?id ?name
        WHERE {{
            ?entity schema:identifier "{input_id}" .
            ?entity schema:creator ?Author .
            ?Author rdfs:label ?name .
            ?Author schema:identifier ?id .
        }}
        """
        df_sparql = get(endpoint, id_author_query, True)
        return df_sparql

    def getCulturalHeritageObjectsAuthoredBy(
        self, input_id
    ) -> pd.DataFrame:  # Ekaterina
        endpoint = self.blazegraph_endpoint
        id_cultural_query = f"""
        PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX schema: <https://schema.org/>

        SELECT ?object ?type_name ?id ?title ?date ?owner ?place ?name ?author_id
            WHERE {{
            ?entity schema:identifier "{input_id}" .
            ?entity schema:creator ?Author .
            ?object schema:creator ?Author .
            ?object rdf:type ?type .
            ?object schema:name ?title .
            ?object schema:identifier ?id .
            ?object schema:dateCreated ?date .
            ?object schema:provider ?owner .
            ?object schema:contentLocation ?place .
            OPTIONAL {{
                ?object schema:creator ?Author .
                ?Author rdfs:label ?name .
                ?Author schema:identifier ?author_id .
            }}
            BIND(REPLACE(STR(?type), "https://schema.org/", "") AS ?type_name)
            FILTER(?type IN (
                    <https://schema.org/NauticalChart>,
                    <https://schema.org/ManuscriptPlate>,
                    <https://schema.org/ManuscriptVolume>,
                    <https://schema.org/PrintedVolume>,
                    <https://schema.org/PrintedMaterial>,
                    <https://schema.org/Herbarium>,
                    <https://schema.org/Specimen>,
                    <https://schema.org/Painting>,
                    <https://schema.org/Model>,
                    <https://schema.org/Map>
                    ))
            }}
            """

        df_sparql = get(endpoint, id_cultural_query, True)
        df_sparql.drop_duplicates(inplace=True)
        return df_sparql


class ProcessDataQueryHandler(QueryHandler):
    def __init__(self):
        super().__init__()

    def getById(self, id: str):  # Rubens
        return pd.DataFrame()

    def getAllActivities(self) -> pd.DataFrame:  # Rubens
        db_file = "json.db"
        try:
            conn = sqlite3.connect(db_file)

            # Use LIKE operator to match partially with the technique string
            query = """
                SELECT object_id, responsible_institute, responsible_person, technique, NULL as tool, start_date, end_date, 'Acquisition' as type  FROM Acquisition
                UNION
                SELECT object_id, responsible_institute, responsible_person, NULL as technique, NULL as tool, start_date, end_date, 'Processing' as type  FROM Processing
                UNION
                SELECT object_id, responsible_institute, responsible_person, NULL as technique, NULL as tool, start_date, end_date, 'Modelling' as type  FROM Modelling
                UNION
                SELECT object_id, responsible_institute, responsible_person, NULL as technique, NULL as tool, start_date, end_date, 'Optimising' as type  FROM Optimising
                UNION
                SELECT object_id, responsible_institute, responsible_person, NULL as technique, NULL as tool, start_date, end_date, 'Exporting' as type  FROM Exporting
            """
            df = pd.read_sql_query(query, conn)
            return df

        except sqlite3.Error as e:
            print("SQLite error:", e)
        finally:
            conn.close()

    def getActivitiesByResponsibleInstitution(
        self, institution_str: str
    ) -> pd.DataFrame:  # Ekaterina
        db_file = "json.db"
        try:
            conn = sqlite3.connect(db_file)

            # Use LIKE operator to match partially with the technique string
            query = """
                SELECT object_id, responsible_institute, responsible_person, technique, NULL as tool, start_date, end_date, 'Acquisition' as type  FROM Acquisition WHERE responsible_institute LIKE ?
                UNION
                SELECT object_id, responsible_institute, responsible_person, NULL as technique, NULL as tool, start_date, end_date, 'Processing' as type  FROM Processing WHERE responsible_institute LIKE ?
                UNION
                SELECT object_id, responsible_institute, responsible_person, NULL as technique, NULL as tool, start_date, end_date, 'Modelling' as type  FROM Modelling WHERE responsible_institute LIKE ?
                UNION
                SELECT object_id, responsible_institute, responsible_person, NULL as technique, NULL as tool, start_date, end_date, 'Optimising' as type  FROM Optimising WHERE responsible_institute LIKE ?
                UNION
                SELECT object_id, responsible_institute, responsible_person, NULL as technique, NULL as tool, start_date, end_date, 'Exporting' as type  FROM Exporting WHERE responsible_institute LIKE ?
            """
            like_param = f"%{institution_str}%"
            params = (like_param, like_param, like_param, like_param, like_param)

            # Fetch the data using pandas
            df = pd.read_sql_query(query, conn, params=params)
            return df

        except sqlite3.Error as e:
            print("SQLite error:", e)
        finally:
            conn.close()

    def getActivitiesByResponsiblePerson(
        self, responsible_person_str: str
    ) -> pd.DataFrame:  # Ben
        db_file = "json.db"
        try:
            conn = sqlite3.connect(db_file)

            # Use LIKE operator to match partially with the technique string
            query = """
                SELECT object_id, responsible_institute, responsible_person, technique, NULL as tool, start_date, end_date, 'Acquisition' as type  FROM Acquisition WHERE responsible_person LIKE ?
                UNION
                SELECT object_id, responsible_institute, responsible_person, NULL as technique, NULL as tool, start_date, end_date, 'Processing' as type  FROM Processing WHERE responsible_person LIKE ?
                UNION
                SELECT object_id, responsible_institute, responsible_person, NULL as technique, NULL as tool, start_date, end_date, 'Modelling' as type  FROM Modelling WHERE responsible_person LIKE ?
                UNION
                SELECT object_id, responsible_institute, responsible_person, NULL as technique, NULL as tool, start_date, end_date, 'Optimising' as type  FROM Optimising WHERE responsible_person LIKE ?
                UNION
                SELECT object_id, responsible_institute, responsible_person, NULL as technique, NULL as tool, start_date, end_date, 'Exporting' as type  FROM Exporting WHERE responsible_person LIKE ?
            """
            like_param = f"%{responsible_person_str}%"
            params = (like_param, like_param, like_param, like_param, like_param)

            df = pd.read_sql_query(query, conn, params=params)
            return df

        except sqlite3.Error as e:
            print("SQLite error:", e)
        finally:
            conn.close()

    def getActivitiesUsingTool(self, tool_str: str) -> pd.DataFrame:  # Rubens
        db_file = "json.db"

        try:
            conn = sqlite3.connect(db_file)

            # Use LIKE operator to match partially with the tool string
            query = """
                SELECT object_id, responsible_institute, responsible_person, technique, NULL as tool, start_date, end_date, 'Acquisition' as type  FROM Acquisition WHERE tool LIKE ?
                UNION
                SELECT object_id, responsible_institute, responsible_person, NULL as technique, NULL as tool, start_date, end_date, 'Processing' as type  FROM Processing WHERE tool LIKE ?
                UNION
                SELECT object_id, responsible_institute, responsible_person, NULL as technique, NULL as tool, start_date, end_date, 'Modelling' as type  FROM Modelling WHERE tool LIKE ?
                UNION
                SELECT object_id, responsible_institute, responsible_person, NULL as technique, NULL as tool, start_date, end_date, 'Optimising' as type  FROM Optimising WHERE tool LIKE ?
                UNION
                SELECT object_id, responsible_institute, responsible_person, NULL as technique, NULL as tool, start_date, end_date, 'Exporting' as type  FROM Exporting WHERE tool LIKE ?
            """
            like_param = f"%{tool_str}%"
            params = (like_param, like_param, like_param, like_param, like_param)

            df = pd.read_sql_query(query, conn, params=params)
            return df

        except sqlite3.Error as e:
            print("SQLite error:", e)
        finally:
            conn.close()

    def getActivitiesStartedAfter(self, start_date: str) -> pd.DataFrame:  # Amanda
        db_file = "json.db"

        try:
            conn = sqlite3.connect(db_file)
            query = """
            SELECT object_id, responsible_institute, responsible_person, technique, NULL as tool, start_date, end_date, 'Acquisition' as type 
            FROM Acquisition WHERE start_date >= ? 
            UNION 
            SELECT object_id, responsible_institute, responsible_person, NULL as technique, NULL as tool, start_date, end_date, 'Processing' as type 
            FROM Processing WHERE start_date >= ? 
            UNION 
            SELECT object_id, responsible_institute, responsible_person, NULL as technique, NULL as tool, start_date, end_date, 'Modelling' as type 
            FROM Modelling WHERE start_date >= ? 
            UNION 
            SELECT object_id, responsible_institute, responsible_person, NULL as technique, NULL as tool, start_date, end_date, 'Optimising' as type 
            FROM Optimising WHERE start_date >= ? 
            UNION 
            SELECT object_id, responsible_institute, responsible_person, NULL as technique, NULL as tool, start_date, end_date, 'Exporting' as type 
            FROM Exporting WHERE start_date >= ?
            """
            df = pd.read_sql_query(
                query,
                conn,
                params=(start_date, start_date, start_date, start_date, start_date),
            )
            return df

        except sqlite3.Error as e:
            print("SQLite error:", e)
        finally:
            conn.close()

    def getActivitiesEndedBefore(self, end_date: str) -> pd.DataFrame:  # Amanda
        db_file = "json.db"

        try:
            conn = sqlite3.connect(db_file)

            # Construct the SQL query with NULL columns where necessary
            query = (
                "SELECT object_id, responsible_institute, responsible_person, technique, NULL as tool, start_date, end_date, 'Acquisition' as type FROM Acquisition WHERE end_date <= ? UNION "
                "SELECT object_id, responsible_institute, responsible_person, NULL as technique, NULL as tool, start_date, end_date, 'Processing' as type FROM Processing WHERE end_date <= ? UNION "
                "SELECT object_id, responsible_institute, responsible_person, NULL as technique, NULL as tool, start_date, end_date, 'Modelling' as type FROM Modelling WHERE end_date <= ? UNION "
                "SELECT object_id, responsible_institute, responsible_person, NULL as technique, NULL as tool, start_date, end_date, 'Optimising' as type  FROM Optimising WHERE end_date <= ? UNION "
                "SELECT object_id, responsible_institute, responsible_person, NULL as technique, NULL as tool, start_date, end_date, 'Exporting' as type FROM Exporting WHERE end_date <= ?"
            )

            df = pd.read_sql_query(
                query, conn, params=(end_date, end_date, end_date, end_date, end_date)
            )
            return df

        except sqlite3.Error as e:
            print("SQLite error:", e)
        finally:
            conn.close()

    def getAcquisitionsByTechnique(self, technique_str: str) -> pd.DataFrame:  # Rubens
        db_file = "json.db"
        try:
            conn = sqlite3.connect(db_file)

            # Use LIKE operator to match partially with the technique string
            query = f"SELECT * FROM Acquisition WHERE technique LIKE ?"

            # Execute the query and pass the technique_str wrapped with '%' for partial match
            df = pd.read_sql_query(query, conn, params=("%" + technique_str + "%",))

            # Add the type column
            df["type"] = "Acquisition"
            return df

        except sqlite3.Error as e:
            print("SQLite error:", e)
        finally:
            conn.close()


class BasicMashup(object):
    def __init__(
        self,
        metadataQuery: List[MetadataQueryHandler],
        processQuery: List[ProcessDataQueryHandler],
    ) -> None:  # Rubens
        self.metadataQuery = metadataQuery if metadataQuery is not None else []
        self.processQuery = processQuery if processQuery is not None else []

    def cleanMetadataHandlers(self) -> bool:  # Rubens
        self.metadataQuery.clear()
        return True

    def cleanProcessHandlers(self) -> bool:  # Rubens
        self.processQuery.clear()
        return True

    def addMetadataHandler(self, handler: MetadataQueryHandler) -> bool:  # Rubens
        self.metadataQuery.append(handler)
        return True

    def addProcessHandler(self, handler: ProcessDataQueryHandler) -> bool:  # Rubens
        self.processQuery.append(handler)
        return True

    def getEntityById(self, id: str) -> IdentifiableEntity | None:  # Rubens
        id_entity: List[Person] = []
        processed_ids = set()  # Set to keep track of processed IDs

        for handler in self.metadataQuery:
            people_df = handler.getById(id)
            for _, row in people_df.iterrows():
                person_id = row["identifier"]
                # Check if the ID has already been processed
                if person_id not in processed_ids:
                    person = Person(id=person_id, name=row["name"])
                id_entity.append(person)
                processed_ids.add(person_id)  # Add the ID to the set of processed IDs

        print("Entity found by Id:")
        for person in id_entity:
            print(
                f"Name: {person.name}, Id: {person.id}, Type: {type(person).__name__}"
            )
        if id_entity == []:
            id_entity = None
            
        return id_entity

    def getAllPeople(self) -> List[Person]:  # Ben/Rubens
        all_people: List[Person] = []
        processed_ids = set()  # Set to keep track of processed IDs

        for handler in self.metadataQuery:
            people_df = handler.getAllPeople()
            for _, row in people_df.iterrows():
                person_id = row["id"]
                # Check if the ID has already been processed
                if person_id not in processed_ids:
                    person = Person(id=person_id, name=row["name"])
                    all_people.append(person)
                    processed_ids.add(
                        person_id
                    )  # Add the ID to the set of processed IDs

        print("Person list created:")
        for person in all_people:
            print(f"Name: {person.name}, Type: {type(person).__name__}")
        return all_people

    def getAllCulturalHeritageObjects(
        self,
    ) -> List[CulturalHeritageObject]:  # Ekaterina
        objects_list = []
        df = pd.DataFrame()

        if len(self.metadataQuery) > 0:
            df = self.metadataQuery[0].getAllCulturalHeritageObjects()
            print("DataFrame returned from SPARQL query:")

        if df.empty:
            print("The DataFrame is empty.")
        else:
            for _, row in df.iterrows():
                id = str(row["id"])
                title = row["title"]
                date = row["date"]
                owner = str(row["owner"])
                place = row["place"]
                author_id = str(row["author_id"])
                author_name = row["author_name"]

                hasAuthor = None
                if author_id and author_name:
                    hasAuthor = [Person(author_id, author_name)]

                try:
                    # Use if-elif-else to instantiate objects based on type name
                    type_name = row["type_name"]
                    if type_name == "NauticalChart":
                        obj = NauticalChart(id, title, date, owner, place, hasAuthor)
                    elif type_name == "ManuscriptPlate":
                        obj = ManuscriptPlate(id, title, date, owner, place, hasAuthor)
                    elif type_name == "ManuscriptVolume":
                        obj = ManuscriptVolume(id, title, date, owner, place, hasAuthor)
                    elif type_name == "PrintedVolume":
                        obj = PrintedVolume(id, title, date, owner, place, hasAuthor)
                    elif type_name == "PrintedMaterial":
                        obj = PrintedMaterial(id, title, date, owner, place, hasAuthor)
                    elif type_name == "Herbarium":
                        obj = Herbarium(id, title, date, owner, place, hasAuthor)
                    elif type_name == "Specimen":
                        obj = Specimen(id, title, date, owner, place, hasAuthor)
                    elif type_name == "Painting":
                        obj = Painting(id, title, date, owner, place, hasAuthor)
                    elif type_name == "Model":
                        obj = Model(id, title, date, owner, place, hasAuthor)
                    elif type_name == "Map":
                        obj = Map(id, title, date, owner, place, hasAuthor)
                    else:
                        print(f"No class defined for type: {type_name}")

                    # Append the instantiated object to the list
                    objects_list.append(obj)
                except ValueError as e:
                    print(f"Error creating CulturalHeritageObject: {e}")

            print("Objects list created:")
            for obj in objects_list:
                print(
                    f"Object ID: {obj.id}, Title: {obj.title}, Type: {obj.__class__.__name__}, hasAuthor: {', '.join([f'{author.name} ({author.id})' for author in obj.hasAuthor]) if obj.hasAuthor else 'None'}"
                )

        return objects_list

    def getAuthorsOfCulturalHeritageObject(
        self, object_id: str
    ) -> List[Person]:  # Ekaterina
        authors_list = []

        for metadata_qh in self.metadataQuery:
            authors_df = metadata_qh.getAuthorsOfCulturalHeritageObject(object_id)
            print(authors_df)

            for _, row in authors_df.iterrows():
                author = Person(row["id"], row["name"])
                authors_list.append(author)

        return authors_list

    def getCulturalHeritageObjectsAuthoredBy(
        self, input_id: str
    ) -> List[CulturalHeritageObject]:  # Ekaterina
        objects_list = []
        df = pd.DataFrame()

        if len(self.metadataQuery) > 0:
            df = self.metadataQuery[0].getCulturalHeritageObjectsAuthoredBy(input_id)
            print("DataFrame returned from SPARQL query:")
            print(df)

        if not df.empty:
            for _, row in df.iterrows():
                id = str(row["id"])
                title = row["title"]
                date = str(row["date"])
                owner = str(row["owner"])
                place = row["place"]
                author_id = str(row["author_id"]) if "author_id" in df.columns else None
                author_name = (
                    row["author_name"] if "author_name" in df.columns else None
                )

                hasAuthor = None
                if author_id and author_name:
                    hasAuthor = [Person(author_id, author_name)]

                try:
                    # Use if-elif-else to instantiate objects based on type name
                    type_name = row["type_name"]
                    if type_name == "NauticalChart":
                        obj = NauticalChart(id, title, date, owner, place, hasAuthor)
                    elif type_name == "ManuscriptPlate":
                        obj = ManuscriptPlate(id, title, date, owner, place, hasAuthor)
                    elif type_name == "ManuscriptVolume":
                        obj = ManuscriptVolume(id, title, date, owner, place, hasAuthor)
                    elif type_name == "PrintedVolume":
                        obj = PrintedVolume(id, title, date, owner, place, hasAuthor)
                    elif type_name == "PrintedMaterial":
                        obj = PrintedMaterial(id, title, date, owner, place, hasAuthor)
                    elif type_name == "Herbarium":
                        obj = Herbarium(id, title, date, owner, place, hasAuthor)
                    elif type_name == "Specimen":
                        obj = Specimen(id, title, date, owner, place, hasAuthor)
                    elif type_name == "Painting":
                        obj = Painting(id, title, date, owner, place, hasAuthor)
                    elif type_name == "Model":
                        obj = Model(id, title, date, owner, place, hasAuthor)
                    elif type_name == "Map":
                        obj = Map(id, title, date, owner, place, hasAuthor)
                    else:
                        print(f"No class defined for type: {type_name}")
                        continue

                    # Append the instantiated object to the list
                    objects_list.append(obj)
                except ValueError as e:
                    print(f"Error creating CulturalHeritageObject: {e}")

            print("Objects list created:")
            for obj in objects_list:
                print(
                    f"Object ID: {obj.id}, Title: {obj.title}, Type: {type(obj).__name__}"
                )

        return objects_list

    def getAllActivities(self) -> List[Activity]:  # Ben/Ekaterina
        all_activities = []
        activities_df = pd.DataFrame()

        if len(self.processQuery) > 0:
            activities_df = self.processQuery[0].getAllActivities()
            print("DataFrame returned from SQL query:")
            print(activities_df)

            for _, row in activities_df.iterrows():
                activity_type = row["type"]
                activity = None  # Initialize activity variable

                # Convert necessary fields to strings
                object_id = str(row["object_id"])
                responsible_institute = str(row["responsible_institute"])
                responsible_person = str(row["responsible_person"])
                tool = str(row["tool"])
                start_date = str(row["start_date"])
                end_date = str(row["end_date"])

                # Create CulturalHeritageObject instance
                cultural_heritage_object = CulturalHeritageObject(
                    object_id, "", "", "", ""
                )

                if activity_type == "Acquisition":
                    technique = str(row["technique"])
                    activity = Acquisition(
                        cultural_heritage_object,
                        responsible_institute,
                        technique,
                        responsible_person,
                        start_date,
                        end_date,
                        tool,
                    )
                elif activity_type == "Processing":
                    activity = Processing(
                        cultural_heritage_object,
                        responsible_institute,
                        responsible_person,
                        tool,
                        start_date,
                        end_date,
                    )
                elif activity_type == "Modelling":
                    activity = Modelling(
                        cultural_heritage_object,
                        responsible_institute,
                        responsible_person,
                        tool,
                        start_date,
                        end_date,
                    )
                elif activity_type == "Optimising":
                    activity = Optimising(
                        cultural_heritage_object,
                        responsible_institute,
                        responsible_person,
                        tool,
                        start_date,
                        end_date,
                    )
                elif activity_type == "Exporting":
                    activity = Exporting(
                        cultural_heritage_object,
                        responsible_institute,
                        responsible_person,
                        tool,
                        start_date,
                        end_date,
                    )

                if activity:
                    all_activities.append(activity)

            print("Activities list created:")
            for activity in all_activities:
                print(
                    f"Activity Type: {type(activity).__name__}, "
                    f"Responsible Institute: {activity.institute}, "
                    f"Responsible Person: {activity.person}, "
                    f"Tool: {activity.tool}, "
                    f"Start Date: {activity.start}, "
                    f"End Date: {activity.end}"
                )

        return all_activities

    def getActivitiesByResponsibleInstitution(
        self, institute_name: str
    ) -> List[Activity]:  # Ben/Ekaterina
        all_activities = []
        activities_df = pd.DataFrame()

        if len(self.processQuery) > 0:
            activities_df = self.processQuery[0].getAllActivities()
            print("DataFrame returned from SQL query:")
            print(activities_df)

            if "type" not in activities_df.columns:
                print("Warning: 'type' column not found in the DataFrame.")
                return all_activities

            for _, row in activities_df.iterrows():
                responsible_institute = str(row["responsible_institute"])

                if institute_name.lower() in responsible_institute.lower():
                    activity_type = row["type"]
                    object_id = str(row["object_id"])
                    responsible_person = str(row["responsible_person"])
                    tool = str(row["tool"])
                    start_date = str(row["start_date"])
                    end_date = str(row["end_date"])

                    cultural_heritage_object = CulturalHeritageObject(
                        object_id, "", "", "", ""
                    )

                    activity = None  # Initialize activity variable
                    if activity_type == "Acquisition":
                        technique = str(row["technique"])
                        activity = Acquisition(
                            cultural_heritage_object,
                            responsible_institute,
                            technique,
                            responsible_person,
                            start_date,
                            end_date,
                            tool,
                        )
                    elif activity_type == "Processing":
                        activity = Processing(
                            cultural_heritage_object,
                            responsible_institute,
                            responsible_person,
                            tool,
                            start_date,
                            end_date,
                        )
                    elif activity_type == "Modelling":
                        activity = Modelling(
                            cultural_heritage_object,
                            responsible_institute,
                            responsible_person,
                            tool,
                            start_date,
                            end_date,
                        )
                    elif activity_type == "Optimising":
                        activity = Optimising(
                            cultural_heritage_object,
                            responsible_institute,
                            responsible_person,
                            tool,
                            start_date,
                            end_date,
                        )
                    elif activity_type == "Exporting":
                        activity = Exporting(
                            cultural_heritage_object,
                            responsible_institute,
                            responsible_person,
                            tool,
                            start_date,
                            end_date,
                        )

                    if activity:
                        all_activities.append(activity)

            print("Activities list created:")
            for activity in all_activities:
                print(
                    f"Activity Type: {type(activity).__name__}, "
                    f"Responsible Institute: {activity.institute}, "
                    f"Responsible Person: {activity.person}, "
                    f"Tool: {activity.tool}, "
                    f"Start Date: {activity.start}, "
                    f"End Date: {activity.end}"
                )

        return all_activities

    def getActivitiesByResponsiblePerson(
        self, person_name: str
    ) -> List[Activity]:  # Ben/Ekaterina
        all_activities = []
        activities_df = pd.DataFrame()

        if len(self.processQuery) > 0:
            activities_df = self.processQuery[0].getAllActivities()
            print("DataFrame returned from SQL query:")
            print(activities_df)

            if "type" not in activities_df.columns:
                print("Warning: 'type' column not found in the DataFrame.")
                return all_activities

            for _, row in activities_df.iterrows():
                responsible_person = str(row["responsible_person"])

                if person_name.lower() in responsible_person.lower():
                    activity_type = row["type"]
                    object_id = str(row["object_id"])
                    responsible_institute = str(row["responsible_institute"])
                    tool = str(row["tool"])
                    start_date = str(row["start_date"])
                    end_date = str(row["end_date"])

                    cultural_heritage_object = CulturalHeritageObject(
                        object_id, "", "", "", ""
                    )

                    activity = None
                    if activity_type == "Acquisition":
                        technique = str(row["technique"])
                        activity = Acquisition(
                            cultural_heritage_object,
                            responsible_institute,
                            technique,
                            responsible_person,
                            start_date,
                            end_date,
                            tool,
                        )
                    elif activity_type == "Processing":
                        activity = Processing(
                            cultural_heritage_object,
                            responsible_institute,
                            responsible_person,
                            tool,
                            start_date,
                            end_date,
                        )
                    elif activity_type == "Modelling":
                        activity = Modelling(
                            cultural_heritage_object,
                            responsible_institute,
                            responsible_person,
                            tool,
                            start_date,
                            end_date,
                        )
                    elif activity_type == "Optimising":
                        activity = Optimising(
                            cultural_heritage_object,
                            responsible_institute,
                            responsible_person,
                            tool,
                            start_date,
                            end_date,
                        )
                    elif activity_type == "Exporting":
                        activity = Exporting(
                            cultural_heritage_object,
                            responsible_institute,
                            responsible_person,
                            tool,
                            start_date,
                            end_date,
                        )

                    if activity:
                        all_activities.append(activity)

            print("Activities list created:")
            for activity in all_activities:
                print(
                    f"Activity Type: {type(activity).__name__}, "
                    f"Responsible Institute: {activity.institute}, "
                    f"Responsible Person: {activity.person}, "
                    f"Tool: {activity.tool}, "
                    f"Start Date: {activity.start}, "
                    f"End Date: {activity.end}"
                )

        return all_activities

    def getActivitiesUsingTool(self, tool_name: str) -> List[Activity]:  # Ben/Ekaterina
        all_activities = []
        activities_df = pd.DataFrame()

        if len(self.processQuery) > 0:
            activities_df = self.processQuery[0].getAllActivities()
            print("DataFrame returned from SQL query:")
            print(activities_df)

            # Check if 'type' column exists
            if "type" not in activities_df.columns:
                print("Warning: 'type' column not found in the DataFrame.")
                return all_activities

            for _, row in activities_df.iterrows():
                tool = str(row["tool"])

                if tool_name.lower() in tool.lower():
                    activity_type = row["type"]
                    object_id = str(row["object_id"])
                    responsible_person = str(row["responsible_person"])
                    responsible_institute = str(row["responsible_institute"])
                    start_date = str(row["start_date"])
                    end_date = str(row["end_date"])

                    cultural_heritage_object = CulturalHeritageObject(
                        object_id, "", "", "", ""
                    )

                    activity = None
                    if activity_type == "Acquisition":
                        technique = str(row["technique"])
                        activity = Acquisition(
                            cultural_heritage_object,
                            responsible_institute,
                            technique,
                            responsible_person,
                            start_date,
                            end_date,
                            tool,
                        )
                    elif activity_type == "Processing":
                        activity = Processing(
                            cultural_heritage_object,
                            responsible_institute,
                            responsible_person,
                            tool,
                            start_date,
                            end_date,
                        )
                    elif activity_type == "Modelling":
                        activity = Modelling(
                            cultural_heritage_object,
                            responsible_institute,
                            responsible_person,
                            tool,
                            start_date,
                            end_date,
                        )
                    elif activity_type == "Optimising":
                        activity = Optimising(
                            cultural_heritage_object,
                            responsible_institute,
                            responsible_person,
                            tool,
                            start_date,
                            end_date,
                        )
                    elif activity_type == "Exporting":
                        activity = Exporting(
                            cultural_heritage_object,
                            responsible_institute,
                            responsible_person,
                            tool,
                            start_date,
                            end_date,
                        )

                    if activity:
                        all_activities.append(activity)

            print("Activities list created:")
            for activity in all_activities:
                print(
                    f"Activity Type: {type(activity).__name__}, "
                    f"Responsible Institute: {activity.institute}, "
                    f"Responsible Person: {activity.person}, "
                    f"Tool: {activity.tool}, "
                    f"Start Date: {activity.start}, "
                    f"End Date: {activity.end}"
                )

        return all_activities

    def getActivitiesStartedAfter(
        self, date: str
    ) -> List[Activity]:  # Amanda/Ekaterina
        all_activities = []
        activities_df = pd.DataFrame()

        if len(self.processQuery) > 0:
            activities_df = self.processQuery[0].getActivitiesStartedAfter(date)
            print("DataFrame returned from SQL query:")
            print(activities_df)

            if "type" not in activities_df.columns:
                print("Warning: 'type' column not found in the DataFrame.")
                return all_activities

            for index, row in activities_df.iterrows():
                activity_type = row["type"]
                object_id = str(row["object_id"])
                tool = str(row["tool"])
                responsible_person = str(row["responsible_person"])
                responsible_institute = str(row["responsible_institute"])
                start_date = str(row["start_date"])
                end_date = str(row["end_date"])

                cultural_heritage_object = CulturalHeritageObject(
                    object_id, "", "", "", ""
                )

                activity = None
                if activity_type == "Acquisition":
                    technique = str(row["technique"])
                    activity = Acquisition(
                        cultural_heritage_object,
                        responsible_institute,
                        technique,
                        responsible_person,
                        start_date,
                        end_date,
                        tool,
                    )
                elif activity_type == "Processing":
                    activity = Processing(
                        cultural_heritage_object,
                        responsible_institute,
                        responsible_person,
                        tool,
                        start_date,
                        end_date,
                    )
                elif activity_type == "Modelling":
                    activity = Modelling(
                        cultural_heritage_object,
                        responsible_institute,
                        responsible_person,
                        tool,
                        start_date,
                        end_date,
                    )
                elif activity_type == "Optimising":
                    activity = Optimising(
                        cultural_heritage_object,
                        responsible_institute,
                        responsible_person,
                        tool,
                        start_date,
                        end_date,
                    )
                elif activity_type == "Exporting":
                    activity = Exporting(
                        cultural_heritage_object,
                        responsible_institute,
                        responsible_person,
                        tool,
                        start_date,
                        end_date,
                    )

                if activity:
                    all_activities.append(activity)

            print("Activities list created:")
            for activity in all_activities:
                print(
                    f"Activity Type: {type(activity).__name__}, "
                    f"Responsible Institute: {activity.institute}, "
                    f"Responsible Person: {activity.person}, "
                    f"Tool: {activity.tool}, "
                    f"Start Date: {activity.start}, "
                    f"End Date: {activity.end}"
                )

        return all_activities

    def getActivitiesEndedBefore(self, date: str) -> List[Activity]:  # Amanda/Ekaterina
        all_activities = []
        activities_df = pd.DataFrame()

        if len(self.processQuery) > 0:
            activities_df = self.processQuery[0].getActivitiesEndedBefore(date)
            print("DataFrame returned from SQL query:")
            print(activities_df)

            if "type" not in activities_df.columns:
                print("Warning: 'type' column not found in the DataFrame.")
                return all_activities

            for index, row in activities_df.iterrows():
                activity_type = row["type"]
                object_id = str(row["object_id"])
                tool = str(row["tool"])
                responsible_person = str(row["responsible_person"])
                responsible_institute = str(row["responsible_institute"])
                start_date = str(row["start_date"])
                end_date = str(row["end_date"])

                cultural_heritage_object = CulturalHeritageObject(
                    object_id, "", "", "", ""
                )

                activity = None
                if activity_type == "Acquisition":
                    technique = str(row["technique"])
                    activity = Acquisition(
                        cultural_heritage_object,
                        responsible_institute,
                        technique,
                        responsible_person,
                        start_date,
                        end_date,
                        tool,
                    )
                elif activity_type == "Processing":
                    activity = Processing(
                        cultural_heritage_object,
                        responsible_institute,
                        responsible_person,
                        tool,
                        start_date,
                        end_date,
                    )
                elif activity_type == "Modelling":
                    activity = Modelling(
                        cultural_heritage_object,
                        responsible_institute,
                        responsible_person,
                        tool,
                        start_date,
                        end_date,
                    )
                elif activity_type == "Optimising":
                    activity = Optimising(
                        cultural_heritage_object,
                        responsible_institute,
                        responsible_person,
                        tool,
                        start_date,
                        end_date,
                    )
                elif activity_type == "Exporting":
                    activity = Exporting(
                        cultural_heritage_object,
                        responsible_institute,
                        responsible_person,
                        tool,
                        start_date,
                        end_date,
                    )

                if activity:
                    all_activities.append(activity)

            print("Activities list created:")
            for activity in all_activities:
                print(
                    f"Activity Type: {type(activity).__name__}, "
                    f"Responsible Institute: {activity.institute}, "
                    f"Responsible Person: {activity.person}, "
                    f"Tool: {activity.tool}, "
                    f"Start Date: {activity.start}, "
                    f"End Date: {activity.end}"
                )

        return all_activities

    def getAcquisitionsByTechnique(self, technique: str):  # Amanda/Ekaterina
        all_activities = []
        activities_df = pd.DataFrame()

        if len(self.processQuery) > 0:
            activities_df = self.processQuery[0].getAcquisitionsByTechnique(technique)
            print("DataFrame returned from SQL query:")
            print(activities_df)

            if "type" not in activities_df.columns:
                print("Warning: 'type' column not found in the DataFrame.")
                return all_activities

            for index, row in activities_df.iterrows():
                activity_type = row["type"]
                object_id = str(row["object_id"])
                tool = str(row["tool"])
                responsible_person = str(row["responsible_person"])
                responsible_institute = str(row["responsible_institute"])
                start_date = str(row["start_date"])
                end_date = str(row["end_date"])

                cultural_heritage_object = CulturalHeritageObject(
                    object_id, "", "", "", ""
                )

                activity = None
                if activity_type == "Acquisition":
                    technique = str(row["technique"])
                    activity = Acquisition(
                        cultural_heritage_object,
                        responsible_institute,
                        technique,
                        responsible_person,
                        start_date,
                        end_date,
                        tool,
                    )

                if activity:
                    all_activities.append(activity)

            print("Activities list created:")
            for activity in all_activities:
                print(
                    f"Activity Type: {type(activity).__name__}, "
                    f"Responsible Institute: {activity.institute}, "
                    f"Responsible Person: {activity.person}, "
                    f"Tool: {activity.tool}, "
                    f"Start Date: {activity.start}, "
                    f"End Date: {activity.end}"
                )

        return all_activities


class AdvancedMashup(BasicMashup):
    def __init__(self, metadataQuery=None, processQuery=None):
        super().__init__(metadataQuery, processQuery)
        
    def getActivitiesOnObjectsAuthoredBy(
        self, author_id: str
    ) -> list[Activity]:  # Rubens
        related_cultural_heritage_objects = self.metadataQuery[0].getCulturalHeritageObjectsAuthoredBy(author_id)

        related_ids = set(related_cultural_heritage_objects["id"])
        print("Related IDs:", related_ids)
        related_ids_str = {str(id) for id in related_ids}

        all_activities = self.processQuery[0].getAllActivities()
        # print(all_activities)

        # Convert object_id column to string (if not already)

        all_activities["object_id"] = all_activities["object_id"].astype(str)
        selected_rows = all_activities[
            all_activities["object_id"].isin(related_ids_str)
        ]
        
        # Convert selected_rows to a list of Activity objects
        activities_list = [Activity(row) for index, row in selected_rows.iterrows()]
        
        return activities_list

    def getObjectsHandledByResponsiblePerson(
        self, responsible_person: str
    ) -> List[CulturalHeritageObject]:  # Ekaterina
        all_objects = []
        if len(self.processQuery) > 0:
            activities_df = self.processQuery[0].getActivitiesByResponsiblePerson(
                responsible_person
            )

            if len(self.metadataQuery) > 0:
                objects_df = self.metadataQuery[0].getAllCulturalHeritageObjects()

                object_ids = []
                for index, row in activities_df.iterrows():
                    activity_id = row["object_id"]
                    if activity_id not in object_ids:
                        object_ids.append(activity_id)
                        object_data = objects_df[objects_df["id"] == activity_id].iloc[
                            0
                        ]
                        object_type = object_data["type_name"]
                        if object_type == "NauticalChart":
                            obj = NauticalChart(
                                id=str(object_data["id"]),
                                title=object_data["title"],
                                date=str(object_data["date"]),
                                owner=str(object_data["owner"]),
                                place=object_data["place"],
                                author_id=(
                                    str(object_data["author_id"])
                                    if "author_id" in objects_df.columns
                                    else None
                                ),
                                author_name=(
                                    object_data["author_name"]
                                    if "author_name" in objects_df.columns
                                    else None
                                ),
                            )
                        elif object_type == "ManuscriptPlate":
                            obj = ManuscriptPlate(
                                id=str(object_data["id"]),
                                title=object_data["title"],
                                date=str(object_data["date"]),
                                owner=str(object_data["owner"]),
                                place=object_data["place"],
                                author_id=(
                                    str(object_data["author_id"])
                                    if "author_id" in objects_df.columns
                                    else None
                                ),
                                author_name=(
                                    object_data["author_name"]
                                    if "author_name" in objects_df.columns
                                    else None
                                ),
                            )
                        elif object_type == "ManuscriptVolume":
                            obj = ManuscriptVolume(
                                id=str(object_data["id"]),
                                title=object_data["title"],
                                date=str(object_data["date"]),
                                owner=str(object_data["owner"]),
                                place=object_data["place"],
                                author_id=(
                                    str(object_data["author_id"])
                                    if "author_id" in objects_df.columns
                                    else None
                                ),
                                author_name=(
                                    object_data["author_name"]
                                    if "author_name" in objects_df.columns
                                    else None
                                ),
                            )
                        elif object_type == "PrintedVolume":
                            obj = PrintedVolume(
                                id=str(object_data["id"]),
                                title=object_data["title"],
                                date=str(object_data["date"]),
                                owner=str(object_data["owner"]),
                                place=object_data["place"],
                                author_id=(
                                    str(object_data["author_id"])
                                    if "author_id" in objects_df.columns
                                    else None
                                ),
                                author_name=(
                                    object_data["author_name"]
                                    if "author_name" in objects_df.columns
                                    else None
                                ),
                            )
                        elif object_type == "PrintedMaterial":
                            obj = PrintedMaterial(
                                id=str(object_data["id"]),
                                title=object_data["title"],
                                date=str(object_data["date"]),
                                owner=str(object_data["owner"]),
                                place=object_data["place"],
                                author_id=(
                                    str(object_data["author_id"])
                                    if "author_id" in objects_df.columns
                                    else None
                                ),
                                author_name=(
                                    object_data["author_name"]
                                    if "author_name" in objects_df.columns
                                    else None
                                ),
                            )
                        elif object_type == "Herbarium":
                            obj = Herbarium(
                                id=str(object_data["id"]),
                                title=object_data["title"],
                                date=str(object_data["date"]),
                                owner=str(object_data["owner"]),
                                place=object_data["place"],
                                author_id=(
                                    str(object_data["author_id"])
                                    if "author_id" in objects_df.columns
                                    else None
                                ),
                                author_name=(
                                    object_data["author_name"]
                                    if "author_name" in objects_df.columns
                                    else None
                                ),
                            )
                        elif object_type == "Specimen":
                            obj = Specimen(
                                id=str(object_data["id"]),
                                title=object_data["title"],
                                date=str(object_data["date"]),
                                owner=str(object_data["owner"]),
                                place=object_data["place"],
                                author_id=(
                                    str(object_data["author_id"])
                                    if "author_id" in objects_df.columns
                                    else None
                                ),
                                author_name=(
                                    object_data["author_name"]
                                    if "author_name" in objects_df.columns
                                    else None
                                ),
                            )
                        elif object_type == "Painting":
                            obj = Painting(
                                id=str(object_data["id"]),
                                title=object_data["title"],
                                date=str(object_data["date"]),
                                owner=str(object_data["owner"]),
                                place=object_data["place"],
                                author_id=(
                                    str(object_data["author_id"])
                                    if "author_id" in objects_df.columns
                                    else None
                                ),
                                author_name=(
                                    object_data["author_name"]
                                    if "author_name" in objects_df.columns
                                    else None
                                ),
                            )
                        elif object_type == "Model":
                            obj = Model(
                                id=str(object_data["id"]),
                                title=object_data["title"],
                                date=str(object_data["date"]),
                                owner=str(object_data["owner"]),
                                place=object_data["place"],
                                author_id=str(object_data["author_id"]),
                                author_name=object_data["author_name"],
                            )
                        elif object_type == "Model":
                            obj = Model(
                                id=str(object_data["id"]),
                                title=object_data["title"],
                                date=str(object_data["date"]),
                                owner=str(object_data["owner"]),
                                place=object_data["place"],
                                author_id=(
                                    str(object_data["author_id"])
                                    if "author_id" in objects_df.columns
                                    else None
                                ),
                                author_name=(
                                    object_data["author_name"]
                                    if "author_name" in objects_df.columns
                                    else None
                                ),
                            )
                        elif object_type == "Map":
                            obj = Map(
                                id=str(object_data["id"]),
                                title=object_data["title"],
                                date=str(object_data["date"]),
                                owner=str(object_data["owner"]),
                                place=object_data["place"],
                                author_id=(
                                    str(object_data["author_id"])
                                    if "author_id" in objects_df.columns
                                    else None
                                ),
                                author_name=(
                                    object_data["author_name"]
                                    if "author_name" in objects_df.columns
                                    else None
                                ),
                            )
                        else:
                            print(f"No class defined for type: {object_type}")
                            continue

                    all_objects.append(obj)

        print("Cultural Heritage Objects list created:")
        for obj in all_objects:
            print(
                f"Object ID: {obj.id}, Title: {obj.title}, Type: {type(obj).__name__}"
            )

        return all_objects

    def getObjectsHandledByResponsibleInstitution(
        self, institute_name: str
    ) -> List[CulturalHeritageObject]:  # Ekaterina
        all_objects = []
        activities_df = pd.DataFrame()

        if len(self.processQuery) > 0:
            activities_df = self.processQuery[0].getActivitiesByResponsibleInstitution(
                institute_name
            )

            if len(self.metadataQuery) > 0:
                objects_df = self.metadataQuery[0].getAllCulturalHeritageObjects()

                object_ids = []
                for _, row in activities_df.iterrows():
                    activity_id = row["object_id"]
                    if activity_id not in object_ids:
                        object_ids.append(activity_id)
                        object_data = objects_df[objects_df["id"] == activity_id].iloc[
                            0
                        ]
                        object_type = object_data["type_name"]
                        if object_type == "NauticalChart":
                            obj = NauticalChart(
                                id=str(object_data["id"]),
                                title=object_data["title"],
                                date=str(object_data["date"]),
                                owner=str(object_data["owner"]),
                                place=object_data["place"],
                                author_id=(
                                    str(object_data["author_id"])
                                    if "author_id" in objects_df.columns
                                    else None
                                ),
                                author_name=(
                                    object_data["author_name"]
                                    if "author_name" in objects_df.columns
                                    else None
                                ),
                            )
                        elif object_type == "ManuscriptPlate":
                            obj = ManuscriptPlate(
                                id=str(object_data["id"]),
                                title=object_data["title"],
                                date=str(object_data["date"]),
                                owner=str(object_data["owner"]),
                                place=object_data["place"],
                                author_id=(
                                    str(object_data["author_id"])
                                    if "author_id" in objects_df.columns
                                    else None
                                ),
                                author_name=(
                                    object_data["author_name"]
                                    if "author_name" in objects_df.columns
                                    else None
                                ),
                            )
                        elif object_type == "ManuscriptVolume":
                            obj = ManuscriptVolume(
                                id=str(object_data["id"]),
                                title=object_data["title"],
                                date=str(object_data["date"]),
                                owner=str(object_data["owner"]),
                                place=object_data["place"],
                                author_id=(
                                    str(object_data["author_id"])
                                    if "author_id" in objects_df.columns
                                    else None
                                ),
                                author_name=(
                                    object_data["author_name"]
                                    if "author_name" in objects_df.columns
                                    else None
                                ),
                            )
                        elif object_type == "PrintedVolume":
                            obj = PrintedVolume(
                                id=str(object_data["id"]),
                                title=object_data["title"],
                                date=str(object_data["date"]),
                                owner=str(object_data["owner"]),
                                place=object_data["place"],
                                author_id=(
                                    str(object_data["author_id"])
                                    if "author_id" in objects_df.columns
                                    else None
                                ),
                                author_name=(
                                    object_data["author_name"]
                                    if "author_name" in objects_df.columns
                                    else None
                                ),
                            )
                        elif object_type == "PrintedMaterial":
                            obj = PrintedMaterial(
                                id=str(object_data["id"]),
                                title=object_data["title"],
                                date=str(object_data["date"]),
                                owner=str(object_data["owner"]),
                                place=object_data["place"],
                                author_id=(
                                    str(object_data["author_id"])
                                    if "author_id" in objects_df.columns
                                    else None
                                ),
                                author_name=(
                                    object_data["author_name"]
                                    if "author_name" in objects_df.columns
                                    else None
                                ),
                            )
                        elif object_type == "Herbarium":
                            obj = Herbarium(
                                id=str(object_data["id"]),
                                title=object_data["title"],
                                date=str(object_data["date"]),
                                owner=str(object_data["owner"]),
                                place=object_data["place"],
                                author_id=(
                                    str(object_data["author_id"])
                                    if "author_id" in objects_df.columns
                                    else None
                                ),
                                author_name=(
                                    object_data["author_name"]
                                    if "author_name" in objects_df.columns
                                    else None
                                ),
                            )
                        elif object_type == "Specimen":
                            obj = Specimen(
                                id=str(object_data["id"]),
                                title=object_data["title"],
                                date=str(object_data["date"]),
                                owner=str(object_data["owner"]),
                                place=object_data["place"],
                                author_id=(
                                    str(object_data["author_id"])
                                    if "author_id" in objects_df.columns
                                    else None
                                ),
                                author_name=(
                                    object_data["author_name"]
                                    if "author_name" in objects_df.columns
                                    else None
                                ),
                            )
                        elif object_type == "Painting":
                            obj = Painting(
                                id=str(object_data["id"]),
                                title=object_data["title"],
                                date=str(object_data["date"]),
                                owner=str(object_data["owner"]),
                                place=object_data["place"],
                                author_id=(
                                    str(object_data["author_id"])
                                    if "author_id" in objects_df.columns
                                    else None
                                ),
                                author_name=(
                                    object_data["author_name"]
                                    if "author_name" in objects_df.columns
                                    else None
                                ),
                            )
                        elif object_type == "Model":
                            obj = Model(
                                id=str(object_data["id"]),
                                title=object_data["title"],
                                date=str(object_data["date"]),
                                owner=str(object_data["owner"]),
                                place=object_data["place"],
                                author_id=str(object_data["author_id"]),
                                author_name=object_data["author_name"],
                            )
                        elif object_type == "Model":
                            obj = Model(
                                id=str(object_data["id"]),
                                title=object_data["title"],
                                date=str(object_data["date"]),
                                owner=str(object_data["owner"]),
                                place=object_data["place"],
                                author_id=(
                                    str(object_data["author_id"])
                                    if "author_id" in objects_df.columns
                                    else None
                                ),
                                author_name=(
                                    object_data["author_name"]
                                    if "author_name" in objects_df.columns
                                    else None
                                ),
                            )
                        elif object_type == "Map":
                            obj = Map(
                                id=str(object_data["id"]),
                                title=object_data["title"],
                                date=str(object_data["date"]),
                                owner=str(object_data["owner"]),
                                place=object_data["place"],
                                author_id=(
                                    str(object_data["author_id"])
                                    if "author_id" in objects_df.columns
                                    else None
                                ),
                                author_name=(
                                    object_data["author_name"]
                                    if "author_name" in objects_df.columns
                                    else None
                                ),
                            )
                        else:
                            print(f"No class defined for type: {object_type}")
                            continue

                        all_objects.append(obj)

        print("Cultural Heritage Objects list created:")
        for obj in all_objects:
            print(
                f"Object ID: {obj.id}, Title: {obj.title}, Type: {type(obj).__name__}"
            )

        return all_objects

    def getAuthorsOfObjectsAcquiredInTimeFrame(
        self, start_date: str, end_date: str
    ) -> list[Person]:  # Rubens
        acquired_authors = []

        activities_started = self.processQuery[0].getActivitiesStartedAfter(start_date)
        started_ids = set(
            activities_started[activities_started["type"] == "Acquisition"]["object_id"]
        )

        activities_ended = self.processQuery[0].getActivitiesEndedBefore(end_date)
        ended_ids = set(
            activities_ended[activities_ended["type"] == "Exporting"]["object_id"]
        )

        common_ids = started_ids.intersection(ended_ids)
        common_ids_int = {int(id) for id in common_ids}
        print("IDs of this timeframe:", common_ids_int)

        for item in common_ids_int:
            authors = self.getAuthorsOfCulturalHeritageObject(item)
            acquired_authors.extend(authors)

        return acquired_authors
