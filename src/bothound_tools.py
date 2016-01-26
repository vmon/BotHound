"""
Utility class that holds commonly used Bothound functions

"""
import numpy as np

import MySQLdb
from features.src.feature_geo import FeatureGEO

from sklearn.cluster import DBSCAN

class BothoundTools():
    def connect_to_db(self):
        """
        This connetcion to the db will live for the live time of the
        learn2bantools instance and will be used to save data back to the db
        """
        self.db = MySQLdb.connect(self.db_host, self.db_user, self.db_password)

        #Create cursor object to allow query execution
        self.cur = self.db.cursor(MySQLdb.cursors.DictCursor)
        sql = 'CREATE DATABASE IF NOT EXISTS ' + self.db_name
        self.cur.execute(sql)

	    #Connect directly to DB
        self.db = MySQLdb.connect(self.db_host, self.db_user, self.db_password, self.db_name)
        self.cur = self.db.cursor(MySQLdb.cursors.DictCursor)

        # ATTACKS table
        self.cur.execute("create table IF NOT EXISTS attacks (id INT NOT NULL AUTO_INCREMENT, "
        "comment LONGTEXT, "
        "PRIMARY KEY(id)) ENGINE=INNODB;")

       # INCIDENTS table
        self.cur.execute("create table IF NOT EXISTS incidents (id INT NOT NULL AUTO_INCREMENT, "
        "id_attack INT,"
        "start DATETIME, "
        "stop DATETIME, "
        "banjax_start DATETIME, "
        "banjax_stop DATETIME, "
        "comment LONGTEXT, "
        "processed BOOL,"
        "PRIMARY KEY(id)) "
        "ENGINE=INNODB;")
        
        # SESSIONS table
        self.cur.execute("create table IF NOT EXISTS sessions (id INT NOT NULL AUTO_INCREMENT, "
        "id_incident INT NOT NULL, "
        "cluster_index INT, "
        "IP VARCHAR(45), "
        "request_interval FLOAT, " #Feature Index 1
        "ua_change_rate FLOAT, " #Feature Index 2
        "html2image_ratio FLOAT, " #Feature Index 3
        "variance_request_interval FLOAT, " #Feature Index 4
        "payload_average FLOAT, " #Feature Index 5
        "error_rate FLOAT, " #Feature Index 6
        "request_depth FLOAT, " #Feature Index 7
        "request_depth_std FLOAT, " #Feature Index 8
        "session_length FLOAT, " #Feature Index 9
        "percentage_cons_requests FLOAT," #Feature Index 10
        "latitude FLOAT," #Feature Index 11
        "longitude FLOAT," #Feature Index 12
        "country VARCHAR(40)," #Feature Index 13
        "PRIMARY KEY(id), INDEX index_incicent (id_incident),  "    
        "FOREIGN KEY (id_incident) REFERENCES incidents(id) ON DELETE CASCADE ) ENGINE=INNODB;")

        # CLUSTERS table
        self.cur.execute("create table IF NOT EXISTS clusters (id INT NOT NULL AUTO_INCREMENT, "
        "id_incident INT NOT NULL, "
        "cluster_index INT NOT NULL, "
        "comment LONGTEXT, "
        "PRIMARY KEY(id), INDEX index_incicent (id_incident),  "    
        "FOREIGN KEY (id_incident) REFERENCES incidents(id) ON DELETE CASCADE ) ENGINE=INNODB;")

    def add_sessions(self, id_incident, ip_feature_db):
        for ip in ip_feature_db:
            insert_sql = "insert into sessions values (" + str(id_incident) + ", 0, " 
            features = ip_feature_db[ip]
            insert_sql += "\"" + ip + "\","
            
            for feature in features:
                insert_sql += str(features[feature]) + ","
                
            insert_sql = insert_sql[:-1]
            insert_sql += ");"
            
            self.cur.execute(insert_sql)
        self.db.commit()

    def get_sessions(self, id_incident):
        self.cur.execute("select * from sessions WHERE id_incident = {0}".format(id_incident))
        return [dict(elem) for elem in self.cur.fetchall()]

    def get_incidents(self, processed):
        self.cur.execute("select id, start, stop from incidents WHERE "
        "cast(processed as unsigned) = %d" % (1 if processed else 0))
        return [dict(elem) for elem in self.cur.fetchall()]

    def get_processed_incidents(self):
        return self.get_incidents(True)

    def get_not_processed_incidents(self):
        return self.get_incidents(False)

    def update_geo(self, id_incident):
        self.cur.execute("select id, ip from sessions WHERE id_incident = {0}".format(id_incident))
        rows = self.cur.fetchall();
        for row in rows:
            match = FeatureGEO.find_location(row['ip'])
            self.cur.execute("update sessions set latitude={}, longitude={}, country='{}'"
            " WHERE id = {}"
            .format(match['latitude'], match['longitude'], match['country'], row['id']))
        return

    def disconnect_from_db(self):
        """
        Close connection to the database
        """
        self.cur.close()
        self.db.close()

    def load_database_config(self, database_conf):        
        self.db_user = database_conf["user"]
        self.db_password = database_conf["password"]
        self.db_host = database_conf["host"]
        self.db_name = database_conf["name"]

    def random_slicer(self, data_size, train_portion=0.5):
        """
        Return two arrays with random true and false and complement of each
        other, used for slicing a set into trainig and testing

        INPUT:
            data_size: size of the array to return
            train_portion: between 0,1 indicate the portion for the True
                           entry
        """
        from random import random
        random_selector = [random() < train_portion for i in range(0, data_size)]
        complement_selector = np.logical_not(random_selector)

        return random_selector, complement_selector

    """
    create a test incident and all the sessions from 
    ../data/feature_db-files.txt
    """
    def get_test_incident(self):

        test_comment = 'Test incident'
        #check if the test incident exists
        self.cur.execute("select id from incidents WHERE comment = '{0}'".format(test_comment))
        for row in self.cur.fetchall():
            print "test incident exists", row['id']
            return row['id']

        print "creating test incident..."

        #new incident record
        sql = "insert into incidents(comment) VALUES('%s')" % (test_comment)
        self.cur.execute(sql)

        id_incident = self.cur.lastrowid;
        print "id_incident", id_incident

        filename = '../data/feature_db-files.txt'
        file = open(filename)
        line_number = 1
        for line in file:
            splitted_line = line.split(') {')

            useful_part = splitted_line[1]
            useful_part = useful_part[:-2]
            new_split = useful_part.split(', ')

            insert_sql = "insert into sessions values (NULL," + str(id_incident) + ", 0, " 
            insert_sql += "\"" + str(line_number) + "\","
            line_number = line_number + 1
            for b in new_split:
               c = b.split(': ')[1]
               insert_sql += str(c) + ","
                
            insert_sql += "0,0,0,"
            insert_sql = insert_sql[:-1]
            insert_sql += ");"
            self.cur.execute(insert_sql)
        
        self.db.commit()
        print "done."
        return id_incident

    """
    Cluster the sessions in the incident.
    Update cluster_index in session table
    Return the sessions with the calculated cluster_index
    """    
    def cluster(self, id_incident):
        sessions = self.get_sessions(id_incident)
        features = [
            "request_interval",
            "ua_change_rate",
            "html2image_ratio",
            "variance_request_interval",
            "payload_average",
            "error_rate",
            "request_depth",
            "request_depth_std",
            "session_length",
            "percentage_cons_requests",
            #"latitude",
            #"longitude"
            ]
        data_set = []
        for session in sessions:
            values = []
            for feature in features:
                values.append(session[feature])
            data_set.append(values)

        if len(data_set) == 0 :
            return

        X = np.array(data_set)

        # Compute DBSCAN
        db = DBSCAN(eps=0.1, min_samples=20).fit(X)        
        core_samples_mask = np.zeros_like(db.labels_, dtype=bool)
        core_samples_mask[db.core_sample_indices_] = True
        labels = db.labels_

        # Number of clusters in labels, ignoring noise if present.
        n_clusters_ = len(set(labels)) - (1 if -1 in labels else 0)
        print('Estimated number of clusters: %d' % n_clusters_)        

        #update the cluster column in session table
        for session, label in zip(sessions, labels):
            session["cluster_index"] = label
            self.cur.execute('update sessions set cluster_index ={0} '
            'where id={1}'.format(label, session['id']))
        self.db.commit()
        return sessions


    def __init__(self, database_conf):
        #we would like people to able to use the tool object even
        #if they don't have a db so we have no reason to load this
        #config in the constructor
        self.load_database_config(database_conf)
        pass


