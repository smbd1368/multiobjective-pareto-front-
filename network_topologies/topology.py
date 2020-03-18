# -*- coding: utf-8 -*-
import sys
sys.dont_write_bytecode
import json
import os
from routing_algorithms.mora import eval_bandwidth_single_link
from routing_algorithms.dijkstra import dijkstra_cost


def write_to_json(data, filename, json_path):
    """
    Write 'data' to json file named 'filename' at 'json_path' location.

    Arguments:
        data {dict} -- data to be written.
        filename {str} -- name of file to be created/overwritten.
        json_path {str} -- relative path of json file to be created/overwritten,
    """

    # Get the complete path
    filepath = os.path.join(json_path, filename)

    # Write data
    with open(filepath + '.json', 'w+') as f:
            json.dump(data, f, sort_keys=True, indent=4)

class Topology:

    def __init__(self, name='topology', node_dict={}, link_dict={}):
        """
        Initialization Method of Topology object.

        Keyword Arguments:
            name {str} -- Name of this Topology. (default: {'topology'})
            node_dict {dict} -- Dictionary of nodes and nodes' properties. (default: {{}})
            link_dict {dict} -- Dictionary of links and links' properties. (default: {{}})
        
        N.B. There are no consistency checks between input node_dict and input link_dict
        """

        self.name = name
        self.nodes=[]               # list of Node objects belonging to this Topology
        self.links=[]               # list of Link objects belonging to this Topology
        self.node_names=[]          # list of node names
        self.link_names=[]          # list of link ids
        self.node_dict = {}         # dictionary of nodes and nodes' properties
        self.link_dict = {}         # dictionary of links and links' properties
        self.current_flows = []     # list of currently applied flows on this Topology

        self.create_topology(node_dict, link_dict)

    # ************ GENERAL PURPOSE METHODS ************

    def create_topology(self, node_dict, link_dict):
        """
        Create nodes and links.
        Arguments:
            node_dict {dict} -- Dictionary of nodes and nodes' properties (default: {{}})
            link_dict {dict} -- Dictionary of links and links' properties (default: {{}})
        """

        # Create nodes
        for node_info in node_dict:
            self.create_node(info=node_dict[node_info])

        # Create links
        for link_info in link_dict:
            self.create_link(info=link_dict[link_info])

    ## NODES

    def create_node(self, info):
        """
        Create a node to be added to this Topology.

        Keyword Arguments:
            info {dict} -- Dictionary of node properties. (default: {{}})
            name {str} -- Node name. (default: {''})
        """
        
        # Create node object
        node = Node(info)

        # Add node to this Topology
        self.add_node(node)


    def add_node(self,node):
        """
        Add 'node' to this Topology.

        Arguments:
            node {Node} -- node to be added.
            info {dict} -- Dictionary of node properties.
        """
        
        # Add node object to this Topology node list 'nodes'
        self.nodes.append(node)

        # Add node name to this Topology node name list 'node_names'
        self.node_names.append(node.name)
        
        # ...add it to this Topology node info dictionary 'node_dict'
        self.node_dict['node{}'.format(len(self.node_dict) + 1)] = node.info


    def get_one_node(self, node_name):
        """
        Return Node object with name 'node_name'.
        
        Arguments:
            node_name {str} -- Name of Node object.
        
        Raises:
            Exception: node not in this Topology.
        
        Returns:
            [Node] -- Node object with name 'node_name'
        """
        
        for node in self.nodes:
            if node.name == node_name:
                return node
        
        raise Exception('*** NODE {} IS NOT IN THIS TOPOLOGY! ***'.format(node_name))


    def update_node_info(self, node):
        
        node_name = node.name
        for n in self.node_dict:
            if  node_name in self.node_dict[n]['_id']:
                self.node_dict[n] = node.info
                break

    ## LINKS

    def create_link(self, info={}):
        """
        Create a link between two nodes of this Topology.

        Keyword Arguments:
            info {dict} -- Dictionary of links and links' properties (default: {{}}) 
        """

        # Create link object
        link = Link(info)
        
        # Add link to this Topology
        self.add_link(link)


    def add_link(self, link):
        """
        Add 'link' to this Topology.

        Arguments:
            info {dict} -- Dictionary of link properties.
        """
        
        # Add link object to this Topology link list 'links'
        self.links.append(link)
        
        # Add link name to this Topology link name list 'link_names'
        self.link_names.append(link.id)
        
        # ... add it to this Topology link info dictionary 'link_dict'
        self.link_dict['link{}'.format(len(self.link_dict) + 1)] = link.info


    def get_one_link(self, link_name):
        """
        Return Link object with id 'link_name'

        Arguments:
            link_name {str} -- ID of Link object.
        
        Raises:
            Exception: link not in this Topology.
        
        Returns:
            [Link] -- Link object with ID 'link_name'
        """

        for link in self.links:
            if link.id == link_name:
                return link
        
        raise Exception('*** LINK {} IS NOT IN THIS TOPOLOGY! ***'.format(link_name))
    

    def update_link_info(self, link):
        
        link_id = link.id
        for l in self.link_dict:
            if  link_id in self.link_dict[l]['_id']:
                self.link_dict[l] = link.info
                break
    
    
    def get_link_between_neighbors(self, nodeA_name, nodeB_name):
        # TODO: write docstrings
        """[summary]
        
        Arguments:
            nodeA_name {[type]} -- [description]
            nodeB_name {[type]} -- [description]
        
        Raises:
            Exception: [description]
            Exception: [description]
        
        Returns:
            [Link] -- Link object between nodeA and nodeB.
        """

        nodeA = self.get_one_node(nodeA_name)
        nodeB = self.get_one_node(nodeB_name)

        # Check if node A and node B are real neighbors
        nodeA_neighbors = nodeA.neighbors_list
        nodeB_neighbors = nodeB.neighbors_list

        if nodeA.name not in nodeB_neighbors:
            raise Exception("*** {} IS NOT {}'s NEIGHBOR! ***".format(nodeA_name,nodeB_name))
        if nodeB.name not in nodeA_neighbors:
            raise Exception("*** {} IS NOT {}'s NEIGHBOR! ***".format(nodeB_name,nodeA_name))
        
        nodeA_links = nodeA.links_list
        for l in nodeA_links:
            link = self.get_one_link(l)
            if link.node1 == nodeA_name and link.node2 == nodeB_name:
                return link
        
        raise Exception("*** UNEXPECTED ERROR: {} AND {} ARE NEIGHBORS BUT NO LINK BETWEEN THEM WAS FOUND!".format(nodeA_name, nodeB_name))

    ## SERVICES

    def get_path(self, src_name, dst_name):
        # TODO: write docstrings

        src = self.get_one_node(src_name)
    
        for key, path in src.spt.items():
            if path[0] == src_name and path[-1] == dst_name:
                return path


    def get_current_flows(self):
        return self.current_flows


    def apply_service_on_network(self, service_flow, path):
        
        # Update current flows
        self.current_flows.append(service_flow)

        for i in range(len(path)-1):
            link = self.get_link_between_neighbors(path[i], path[i+1])
            link.apply_service_on_link(service_flow)
            self.update_link_info(link) 
        self.save_topology_info()     


    def remove_service_from_network(self, service_flow, path):
        
        # Update current flows
        self.current_flows.remove(service_flow)

        for i in range(len(path)-1):
            link = self.get_link_between_neighbors(path[i], path[i+1])
            link.remove_service_from_link(service_flow)
            self.update_link_info(link)
        self.save_topology_info()        

    def get_reliability_score(self):
        reliabilities = [eval_bandwidth_single_link(x.bandwidth_usage) for x in self.links]
        return max(reliabilities)

    def get_power_consumption(self):
        powers = [x.power_consumption_MORA for x in self.links]
        return sum(powers)

    ## TOPO OBJECT

    def save_topology_info(self):
        """
        Save topology info.
        
        'node_dict' and 'link_dict' are saved in folder ."self.name"/"self.name"DB/
        respectively in the files nodes.json and links.json.

        """

        # Build up database_path
        current_dir = os.path.dirname(__file__)
        database_folder = self.name + 'DB'
        database_path = os.path.join(current_dir, self.name, database_folder)
        
        # If it doesn't exists, create it
        if not os.path.exists(database_path):
            os.mkdir(database_path)

        # Save nodes and links data
        write_to_json(self.node_dict, 'nodes', database_path)
        write_to_json(self.link_dict, 'links', database_path)
    
    ## ADJACENCY MATRICES

    def get_adjacency_matrix(self):
        """
        Return Topology adjacency matrix.

        Returns:
            [list] -- Topology Adjacency matrix. 
        """
        adj_matrix = [[ 0 for i in range(len(self.nodes))] for j in range(len(self.nodes))]
        sorted_nodes = sorted(self.node_names)
        for i in range(len(self.nodes)):
            node_i = sorted_nodes[i]
            for j in range(len(self.nodes)):
                node_j = sorted_nodes[j]
                if self.is_connection_possible(node_i, node_j):
                    adj_matrix[sorted_nodes.index(node_i)][sorted_nodes.index(node_j)] = 1
        
        return adj_matrix


    def get_operational_adjacency_matrix(self):
        """
        Return Topology operational adjacency matrix.

        The difference between op_adj_matrix and adj_matrix is that the former takes into account
        the status of a link.

        Returns:
            [list] -- Topology Operational Adjacency matrix. 
        """
        
        # Initialize adj_matrix (i: rows index, j: columns index)
        op_adj_matrix = [[ 0 for i in range(len(self.nodes))] for j in range(len(self.nodes))]

        # Consider i-th row:
        for i in range(len(self.nodes)):
            # get i-th node from node_names..
            node_i = self.node_names[i]

            for j in range(len(self.nodes)):
                # ..and get j-th node from node_names too.
                node_j = self.node_names[j]
                
                # Consider the following link id:
                link_name = node_i + node_j

                # If it is in 'link_names' list..
                if link_name in self.link_names:
                    # ..link exists...
                    
                    link = self.get_one_link(link_name)

                    if link.status == 'on':
                        op_adj_matrix[i][j] = 1  # ..and it is turned on: 1
                    else:
                        op_adj_matrix[i][j] = 0  # ..but it is switched off: 0
                
                else:
                    op_adj_matrix[i][j] = 0  #..otherwise, link doesn't exists: 0.
        
        return op_adj_matrix


    def __repr__(self):
        
        adj_matrix=self.get_adjacency_matrix()        
        rep = '**** ADJACENCY MATRIX ****\n'  
        rep += '\n' 
        node_names = sorted(self.node_names)
        rep += '     '
        for i in range(len(adj_matrix)):
            rep += node_names[i] + '    '
        rep +=  '\n'    
        for i in range(len(adj_matrix)):
            rep +=' ' + node_names[i]
            for j in range(len(adj_matrix)):
                if adj_matrix[i][j] == 1:
                    rep += ' [xx] '
                else:
                    rep += ' [  ] '
            rep +=  '\n'
        
        rep += '**************************'
        
        return rep


    def pretty_print_adjacency_matrix(self, adj_matrix):
        """
        Print adjacency matrix in a human readable form.

        Arguments:
            adj_matrix {list} -- Topology Adjacency matrix.

        N.B. Node names must be all of the same length (for now). 
        """

        print('**** ADJACENCY MATRIX ****')
        print('')

        for i in range(len(adj_matrix)):
            begin_of_row = ' ' + self.node_names[i] + ' '
            print(begin_of_row, end='')
            for j in range(len(adj_matrix)):
                if adj_matrix[i][j] == 1:
                    print(' [xx] ', end='')
                else:
                    print(' [  ] ', end='')
            print('\n')
        
        print('**************************')


    # ************ DIJKSTRA ANCILLARY METHODS ************

    def dijkstra_cost_matrix(self):
        # TODO: write docstrings
        """[summary]
        
        Returns:
            [type] -- [description]
        """

        # Initialize cost_matrix (i: rows index, j: columns index)
        cost_matrix = self.get_operational_adjacency_matrix()

        # Consider i-th row:
        for i in range(len(self.nodes)):
            # get i-th node from node_names..
            node_i = self.node_names[i]

            for j in range(len(self.nodes)):
                # ..and get j-th node from node_names too.
                node_j = self.node_names[j]

                # Check if node_i and node_j are neighbors...
                if cost_matrix[i][j] == 1:
                    # ..if so, get the cost of the link between them..
                    link_ij = self.get_link_between_neighbors(node_i, node_j)
                    cost_ij = dijkstra_cost(link_ij.total_bandwidth)
                    # ..and update cost matrix [i][j] with the actual cost.
                    cost_matrix[i][j] = cost_ij
                else:
                    # .., otherwise, link doesn't exists: set cost to infinity.
                    cost_matrix[i][j] = float("inf")

        return cost_matrix

    # ************ EAR ANCILLARY METHODS ******************

    def switch_off_link(self, link):
        # TODO: write docstrings

        link.status = 'off'
        self.update_link_info(link)
        
        # UPDATE NODE 1
        node1_obj = self.get_one_node(link.node1)
        node1_obj.shutdown_link(link)
        self.update_node_info(node1_obj)

        # UPDATE NODE 2
        node2_obj = self.get_one_node(link.node2)
        node2_obj.shutdown_link(link)
        self.update_node_info(node2_obj)


    def turn_on_link(self,link):
        # TODO: write docstrings

        link.status = 'on'
        self.update_link_info(link)
        
        # UPDATE NODE 1
        node1_obj = self.get_one_node(link.node1)
        node1_obj.shutdown_link(link)
        self.update_node_info(node1_obj)

        # UPDATE NODE 2
        node2_obj = self.get_one_node(link.node2)
        node2_obj.shutdown_link(link)
        self.update_node_info(node2_obj)


    def change_node_role(self, node, role):
        # TODO: write docstrings

        node.role = role
        self.update_node_info(node)

    # ************ MORA ANCILLARY METHODS ************

    def is_connection_possible(self, node_1, node_2):
        node_1_links = self.get_valid_links(node_1)
        if node_2 in node_1_links:
            return True
        else:
            return False

    def get_valid_links(self, node):
        #valid_links = []
        """
        node_links = self.get_operational_adjacency_matrix()[int(node)]
        for idx in range(len(node_links)):
            if node_links[idx] != 0:
                valid_links.append(idx)
        """
        n = [x for x in self.nodes if x.name == node][0]
        node_links = n.neighbors_list

        return sorted(node_links)

    def has_loops(self, path):
        has_loops = (len(path) != len(set(path)))                                                                     
        return has_loops 


    def is_valid(self, path):
        for idx in range(len(path)-1):
            if path[idx+1] not in self.get_valid_links(path[idx]):
                return False
        return True

class Node:
 
    def __init__(self, info):
        """
        Initialization Method of Node object.

        Keyword Arguments:
            info {dict} -- This Node properties.
        
        """
              
        # Parse input 'info' and initialize object variables

        # ------------------ PHYSICAL STATE ----------------------------------
        self.name = info["_id"]
        self.pop = info["pop"]
        self.links = info["links"]
        self.links_list = list(self.links.values())
        self.neighbors = info["neighbors"]
        self.neighbors_list = list(self.neighbors.values())
        #
        # ---------------------------------------------------------------------

        # --------------------- OPERATIONAL STATE -----------------------------
        #
        self.active_links = self.links.copy()
        self.active_links_list = self.links_list.copy()
        self.active_neighbors = self.neighbors.copy()
        self.active_neighbors_list = self.neighbors_list.copy()
        #
        # ---------------------------------------------------------------------

        # Other properties
        self._role = 'NR'  # default role
        self._info = {}  # initialize self.info

        self.update_info()


    @property
    def role(self):
        return self._role
    

    @role.setter
    def role(self, new_value):
        
        possible_values = ['NR', 'ER', 'IR']

        if new_value in possible_values:
            self._role = new_value
            self.update_info()
        else:
            raise Exception("*** {} IS NOT A VALID ROLE! ***".format(new_value))


    def update_info(self):

        info = {"_id": self.name,
                "pop": self.pop,
                "links": self.links,
                "links_list": self.links_list,
                "active_links": self.active_links,
                "active_links_list": self.active_links_list,
                "neighbors": self.neighbors,
                "neighbors_list": self.neighbors_list,
                "active_neighbors": self.active_neighbors,
                "active_neighbors_list": self.active_neighbors_list,
                "role": self.role
                }
                
        self.info = info


    def shutdown_link(self, link):
        # TODO: write docstrings
        """
        
        Arguments:
            link {[type]} -- [description]
        
        Raises:
            exception.: [description]
            Exception: [description]
        """

        # Check if provided link belongs to this node and get this node neighbor...
        if link.node1 == self.name:
            neighbor = link.node2
        elif link.node2 == self.name:
            neighbor = link.node1
        else:
            # ...otherwise raise exception.
            raise Exception("*** LINK {} DOES NOT BELONG TO THIS NODE {}".format(link.name, self.name))
        
        # ------------ UPDATE LINKS -----------------
        #
        self.active_links_list.remove(link.id)
        
        self.active_links = {}  # re-initialize active_links
        i = 1
        
        for act_link in self.active_links_list:
            self.active_links["link{}".format(i)] = act_link
            i+=1
        #
        # -----------------------------------------------

        # ------------ UPDATE NEIGHBORS -----------------
        #
        self.active_neighbors_list.remove(neighbor)

        self.active_neighbors = {}  # re-initialize active_neighbors
        i = 1

        for act_neighbor in self.active_neighbors_list:
            self.active_neighbors["neighbor{}".format(i)] = act_neighbor
            i+=1
        #
        #-------------------------------------------------

        self.update_info()

    
    def startup_link(self, link):
        # TODO: write docstrings
        """[summary]
        
        Raises:
            exception.: [description]
            Exception: [description]
        """

        # Check if provided link belongs to this node and get this node neighbor...
        if link.node1 == self.name:
            neighbor = link.node2
        elif link.node2 == self.name:
            neighbor = link.node1
        else:
            # ...otherwise raise exception.
            raise Exception("*** LINK {} DOES NOT BELONG TO THIS NODE {}".format(link.name, self.name))
        
        # ------------ UPDATE LINKS -----------------
        #
        self.active_links_list.append(link.id)
        
        self.active_links = {}  # re-initialize active_links
        i = 1
        
        for act_link in self.active_links_list:
            self.active_links["link{}".format(i)] = act_link
            i+=1
        #
        # -----------------------------------------------

        # ------------ UPDATE NEIGHBORS -----------------
        #
        self.active_neighbors_list.append(neighbor)

        self.active_neighbors = {}  # re-initialize active_neighbors
        i = 1

        for act_neighbor in self.active_neighbors_list:
            self.active_neighbors["neighbor{}".format(i)] = act_neighbor
            i+=1
        #
        #-------------------------------------------------

        self.update_info()


class Link:
    
    def __init__(self, info):
        """
        Initialization Method of Link Object.

        Link is a directed edge, from node1 to node2 edges.
        (node1) >>>>>>>> link >>>>>>>> (node2)

        Arguments:
            info {dict} -- This Link properties.

        """

        # Parse input 'info' and initialize object variables

        # ------------------------- PHYSICAL STATE ----------------------------
        #
        self.node1 = info["node1"]          # first link endpoint
        self.node2 = info["node2"]          # second link endpoint
        self.id = self.node1 + self.node2   # link id
        self.total_bandwidth = info["bw"]   # capacity [Mbps]
        self.len = info["len"]              # length [Km]
        self.latency = info["delay"]        # latency [ms]
        self.jitter = info["jitter"]        # jitter [ms]
        self.loss = info["loss"]            # packet loss [%]
        #
        # ---------------------------------------------------------------------

        # --------------------- OPERATIONAL STATE -----------------------------
        #
        self._status = 'on'                 # status: on/off
        self.consumed_bandwidth = 0.0       # used capacity [Mbps]
        self.bandwidth_usage = 0.0          # used capacity [%]
        self.service_flows = []             # flows coupled to this Link
        self.power_consumption = 0.0        # power consumption [Kwh]
        self.power_consumption_MORA = 0.0   # power consumption [W]
        #
        # ---------------------------------------------------------------------

        self.update_info()


    @property
    def status(self):
        return self._status
    

    @status.setter
    def status(self, new_value):
        
        possible_values = ['on', 'off']

        if new_value in possible_values:
            self._status = new_value
            self.update_info()
        else:
            raise Exception("*** {} IS NOT A VALID STATUS! ***".format(new_value))

    
    def update_info(self):
        # TODO: write docstrings
        """
        [summary]
        """

        info = {"_id": self.id,
                "node1": self.node1, 
                "node2": self.node2,
                "bw": self.total_bandwidth, 
                "len": self.len,
                "delay": self.latency,
                "jitter": self.jitter,
                "loss": self.loss,
                "status": self.status,
                "bw_usage": self.bandwidth_usage,
                "consumed_bw": self.consumed_bandwidth,
                "service_flows": self.service_flows,
                "power_consumption": self.power_consumption
                }
                
        self.info = info


    def apply_service_on_link(self, service_flow):
        # TODO: write docstrings
        """
        [summary]
        """

        service_flow_id = service_flow["_id"]
        service_flow_bandwidth = service_flow["bandwidth"]

        self.service_flows.append(service_flow_id)
        self.consume_bandwidth(service_flow_bandwidth)

        self.update_info()


    def remove_service_from_link(self, service_flow):
        # TODO: write docstrings
        """
        [summary]
        """

        service_flow_id = service_flow["_id"]
        service_flow_bandwidth = - service_flow["bandwidth"]

        self.service_flows.remove(service_flow_id)
        self.consume_bandwidth(service_flow_bandwidth)

        self.update_info()


    def consume_bandwidth(self, required_bandwidth):
        # TODO: write docstrings
        """
        [summary]
        """
       
        self.consumed_bandwidth = self.consumed_bandwidth + float(required_bandwidth)

        if self.consumed_bandwidth > self.total_bandwidth:
            self.bandwidth_usage = 1
        else:
            self.bandwidth_usage = self.consumed_bandwidth/self.total_bandwidth       

        # Updating power consumption based on new link occupation
        self.power_consumption_MORA = self.get_power_consumption(self.consumed_bandwidth)
        self.update_info()

    def get_power_consumption(self, x, delta = 180, rho = 5e-4, mu = 1e-03, alpha = 1.4, n_l = 1):
        # See paper "A Hop-by-Hop Routing Mechanismfor Green Internet"
        # Link energy model used for "hop by hop..." and MORA
        return 2*n_l*(delta + rho*(x/n_l) + mu * ((x/n_l)**alpha))