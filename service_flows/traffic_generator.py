# -*- coding: utf-8 -*-
import sys
sys.dont_write_bytecode
import json
import threading
import time, datetime
import os
import pandas as pd
import numpy as np 

class TrafficGenerator():

    def __init__(self, interval, topology, path=os.path.dirname(__file__), faults = 0):
        
        #### CONSTANT PARAMETERS ####
        self.p_part = 0.16
        self.a_part = 0.67
        self.be_part = 1 - (self.p_part + self.a_part)  # 0.17

        self.premium_thresh = 150 #ms
        self.assured_thresh = 400 #ms

        #### ATTRIBUTES ####
        self.flows = {}
        self.interval = interval
        self.topo = topology
        self.old_path_archive = []
        self.new_path_archive = []

        #### TRAFFIC MATRICES ####
        self.path = os.path.join(path, 'traffic_matrices')

        # Get Traffic files & sort them
        self.traffic_files = [f for f in os.listdir(self.path)]
        self.traffic_files.sort(key=str.lower)

        # Program node faults
        self.faults_number = faults
        self.fault_generator()
        # Create thread
        thread = threading.Thread(target=self.generate_flows, args=())
        thread.daemon = True
        thread.start()

        ### LOGGING ###
        self.starting_time = datetime.datetime.now()
        self.log_file_name = "log_{}_{}.csv".format(\
                self.starting_time.strftime("%Y-%m-%d %H:%M:%S"), topology.routing_method)

        df = pd.DataFrame(columns=['Routing algorithm', 'Power consumption [W]', 'Reliability score (Max)',\
                            'Reliability score (Mean)', 'Mean latency (premium) [ms]',\
                            'Mean latency (assured) [ms]: ', 'Premium SLA violations:', 'Assured SLA violations:',
                            'Mean Premium SLA violations:' , 'Mean Assured SLA violations:'])
        df.to_csv(self.log_file_name, mode='w', header=True)

    def generate_flows(self):
        
        i = 0
        
        while i < len(self.traffic_files):
            # Check if any node will fail
            for _, fault in enumerate(self.faults):
                if fault[0] == i:
                    self.topo.shutdown_node(fault[1])
                    self.topo.faulty_node_list.append(fault[1])     



            flows = {}
            f_path = os.path.join(self.path, self.traffic_files[i])
            f = read_from_json(f_path)

            for src in f:
                for dst in f[src]:
                    bw = round(f[src][dst]/1000000,0)  # Get traffic bandwidth from src to dst and convert in Mbps
                    if bw > 0:
                        bw_p = round(self.p_part * bw, 3)  # premium bandwidth
                        bw_a = round(self.a_part * bw, 3)  # assured bandwidth
                        bw_be = round(self.be_part * bw, 3)  # best effort bandwidth
                        flows['{}{}{}'.format(src, dst, 'premium')] = self.get_flow(service_class='premium', bandwidth=bw_p, nodeA=src, nodeB=dst)
                        flows['{}{}{}'.format(src, dst, 'assured')] = self.get_flow(service_class='assured', bandwidth=bw_a, nodeA=src, nodeB=dst)
                        flows['{}{}{}'.format(src, dst, 'besteffort')] = self.get_flow(service_class='besteffort', bandwidth=bw_be, nodeA=src, nodeB=dst)
            self.flows = flows
            i+=1
            self.apply_flows()
            time.sleep(self.interval)

    def get_flow(self, service_class, bandwidth, nodeA, nodeB):
        """[summary]
        
        Arguments:
            service_class {[type]} -- [description]
            bandwidth {[type]} -- [description]
            nodeA {[type]} -- [description]
            nodeB {[type]} -- [description]
        
        Returns:
            [type] -- [description]
        """
        
        flow_id = nodeA + nodeB + service_class
        flow_constraints = self.class_performance_constraints(service_class)

        service_flow = {
            "_id": flow_id,
            "node1": nodeA,
            "node2": nodeB,
            "bandwidth": bandwidth
        }

        service_flow.update(flow_constraints)
        
        return service_flow

    def class_performance_constraints(self, service_class):    
        """[summary]
        
        Arguments:
            service_class {[type]} -- [description]
        
        Returns:
            [type] -- [description]
        """
        
        if service_class == 'premium':
            latency = 150  # ms
            jitter = 0
            loss = 0
        elif service_class == 'assured':
            latency = 400  # ms
            jitter = 0
            loss = 0
        else:
            latency = 300000  # ms --> 5 minutes = infinite time!
            jitter = 0
            loss = 0
        
        performance_constraints = {
            'latency': latency,
            'jitter': jitter,
            'loss': loss
        }

        return performance_constraints

    def apply_flows(self):

        # Bandwidth threshold: if two flows with equal source-destination are found between
        # two time intervals, check their bandwidth
        # If difference > threshold, then consider them as different flows
        bw_delta_thrs = 100  # Mbps        
        if not self.old_path_archive:

            ## APPLY FLOWS ON NETWORK (THE NETWORK IS EMPTY)
            for _, flow in self.flows.items():
                #node1 = flow["node1"]
                #node2 = flow["node2"]
                #flow_path = self.topo.get_shortest_path(node1, node2)
                flow_path = self.topo.get_path(flow)
                self.new_path_archive.append((flow, flow_path))
                self.topo.apply_service_on_network(flow, flow_path)
        
        else:
            ## APPLY/MODIFY FLOWS ON NETWORK
            # Topology not empty, evaluate if new flows correspond to old flows
            for _, flow in self.flows.items():
                
                # If the current flow source/destination has faulted, the flow is not considered
                if flow["node1"] in self.topo.faulty_node_list \
                    or flow["node2"] in self.topo.faulty_node_list:
                    continue
                #node1 = flow["node1"]
                #node2 = flow["node2"]
                #flow_path = self.topo.get_path(node1, node2)
                #presence_flag = False
                # Check if flow is currently applied on topology...

                flow_exist = [x for x in self.old_path_archive if x[0]["_id"] == flow["_id"]]

                if flow_exist: 
                    # A flow with the same id exist, check if it's a random fluctuation
                    # presence_flag = True
                    old_entry = flow_exist[0]
                    if abs(old_entry[0]["bandwidth"] - flow["bandwidth"]) > bw_delta_thrs:
                        # It's a new flow, discard the old one and route this one                    
                        self.topo.remove_service_from_network(old_entry[0], old_entry[1])
                        self.old_path_archive.remove(old_entry)
                        flow_path = self.topo.get_path(flow)
                        self.new_path_archive.append((flow, flow_path))
                        self.topo.apply_service_on_network(flow, flow_path)
                    else:
                        # It's an old flow, remove it from old list, put it into new list                    
                        self.old_path_archive.remove(old_entry)
                        self.new_path_archive.append(old_entry)  
                else:  
                    # It's a new flow, route it and log it
                    flow_path = self.topo.get_path(flow)
                    self.new_path_archive.append((flow, flow_path))
                    self.topo.apply_service_on_network(flow, flow_path)

            ## REMOVE TERMINED FLOWS FROM NETWORK
            # Remove all flows that are not alive anymroe
            # All old flows that are not matched in new flows
            # Everything left in old flows
            for entry in self.old_path_archive:
                self.topo.remove_service_from_network(entry[0], entry[1])

        self.old_path_archive = self.new_path_archive
        self.new_path_archive = []
        self.topo.update_link_status()
        self.log_stats()

    def log_stats(self):
        """
        Called at the end of every new flow cycle, log network wide stats
        * Network-wide energy consumption
        * Network-wide reliability score (max and mean)
        * # of SLA violation
        * Mean latency per flow class
        * ?
        """ 
        max_rel, mean_rel = self.topo.get_reliability_score()
        premium_lat = []
        assured_lat = [] 
        premium_violations = 0
        assured_violations = 0
        mean_premium_violations = []
        mean_assured_violations = []

        for f in self.old_path_archive:
            if 'premium' in f[0]['_id']:
                path_lat = []
                for j in range(len(f[1])-1):
                    link = self.topo.get_link_between_neighbors(f[1][j], f[1][j+1])
                    path_lat.append(link.latency)
                    path_lat = np.mean(path_lat)
                    premium_lat.append(path_lat)
                    if path_lat > self.premium_thresh:
                        premium_violations += 1
                        mean_premium_violations.append(abs(path_lat - self.premium_thresh))

            elif 'assured' in f[0]['_id']:
                path_lat = []
                for j in range(len(f[1])-1):
                    link = self.topo.get_link_between_neighbors(f[1][j], f[1][j+1])
                    path_lat.append(link.latency)
                    path_lat = np.mean(path_lat)
                    assured_lat.append(path_lat)
                    if path_lat > self.assured_thresh:
                        assured_violations += 1
                        mean_assured_violations.append(abs(path_lat - self.assured_thresh))

        header = {'Routing algorithm':[self.topo.routing_method], \
                  'Power consumption [W] ':[self.topo.get_power_consumption()], \
                  'Reliability score (Max)':[max_rel], 'Reliability score (Mean)':[mean_rel],\
                  'Mean latency (premium)': [np.mean(premium_lat)], \
                  'Mean latency (assured):': [np.mean(assured_lat)], \
                  'Premium SLA violations:': [premium_violations], \
                  'Assured SLA violations:': [assured_violations], \
                  'Mean Premium SLA violations:': [np.mean(mean_premium_violations)],\
                  'Mean Assured SLA violations:': [np.mean(mean_assured_violations)]} 

        df = pd.DataFrame(header)
        df.to_csv(self.log_file_name, mode='a', header=False)

        return

    def fault_generator(self):
        # When are the faults going to occur?
        if self.faults_number is not 0:
            self.faults = []
            fault_times = np.random.choice(len(self.traffic_files), size = self.faults, replace = False)
        # Which nodes are going to fault?
        faulty_nodes = np.random.choice(len(self.topo.nodes), size = len(fault_times), replace = False)
        # Create the structure of faults
        # Format: 
        # fault time = i -> the node is going to fail before loading traffic file i
        # faulty_nodes = j -> the j node is going to fail at time i
        for n in self.faults_number:
            self.faults.append((fault_times[n], self.topo.nodes(faulty_nodes[n].name)))
        return

def read_from_json(json_path):
    """
    Returns data read from json file at found at 'json_path' location.

    Arguments:
        json_path {str} -- relative path of json file to be read.

    Returns:
        [dict] -- Dictionary with data read from json.
    """

    # Read data
    with open(json_path, 'r') as json_file:
        data = json.load(json_file)
    
    return data
