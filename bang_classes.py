import socket
import select
import json
import copy

HOST = 'localhost'
PORT = 5000
RECV_BUFFER = 4096


class Clients(object):

    def __init__(self, host, port):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.client_socket.connect((host, port))
            print 'Successfully connected to server'
        except socket.error:
            print 'Unable to connect to server'
            pass

    def _send_msg(self, msg):
        try:
            self.client_socket.sendall(msg)
        except socket.error:
            print 'Unable to send message'
            pass

    def run(self):
        while True:
            try:
                data = self.client_socket.recv(RECV_BUFFER)
            except socket.error:
                break


class Server(object):

    def __init__(self, server_name):
        """
        _socket_list: list of sockets connected
        _ip_2_info: dict to track down players' info from their IPs
        _name_2_info: dict to track down players' info from their names
        _name_2_ip: dict to track down players' IP from their names

        :param server_name: name of the server
        :return: None
        """
        self._socket_list = []
        self._ip_2_info = {}
        self._name_2_ip = {}
        self._name_2_info = {}

        self._name = server_name
        self._server_socket = None

        self._turn = 0

    def init(self, host, port):
        self._server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._server_socket.bind((host, port))
        self._socket_list.append(self._server_socket)
        self._server_socket.listen(10)
        print 'Server created'

    # ************************************ #
    # **********BANG FUNCTIONS************ #
    # ************************************ #

    def process(self, data):
        """
        :param data: a dict of template {'Sender': sender, 'Action': action, 'Target': target}
        :return: None
        """
        sender = data['Sender']
        action = data['Action']
        target = self._name_2_ip[data['Target']]
        if action == 'BANG':
            self.get_banged(target)
        elif action == 'BEER':
            self.gain_hp(target)

    def get_banged(self, target_ip):

        pass

    def lose_hp(self, target_ip):
        self._ip_2_info[target_ip]['hit_points'] -= 1 if (target_ip in self._ip_2_info) else None

    def lose_card(self, target_ip, card):
        self._ip_2_info[target_ip]['cards'].remove(card) if (target_ip in self._ip_2_info) else None

    def gain_hp(self, target_ip):
        self._ip_2_info[target_ip]['hit_points'] += 1 if (target_ip in self._ip_2_info) else None

    def gain_card(self, target_ip, card):
        self._ip_2_info[target_ip]['cards'].append(card) if (target_ip in self._ip_2_info) else None

    def change_turn(self):
        if self._turn < len(self._socket_list):
            self._turn += 1
        else:
            self._turn = 0

    # ************************************ #
    # ************END FUNCTIONS*********** #
    # ************************************ #

    def broadcast(self, msg, sender_socket=None):
        for a_socket in self._socket_list:
            # send the message only to peer
            if (a_socket != self._server_socket) and (a_socket != sender_socket):
                try:
                    a_socket.send(msg)
                except socket.error:
                    a_socket.close()
                    self._socket_list.remove(a_socket) if a_socket in self._socket_list else None

    def respond(self):
        """
        respond to a client, meaning broadcast the current state (updated) to all clients
        :param: None
        :return: None
        """
        data = json.dumps(self._name_2_info)
        self.broadcast(data)

    def run(self):
        ready_to_read, _, _ = select.select(self._socket_list, [], [], 0)
        for current_socket in ready_to_read:
            if current_socket == self._server_socket:  # a new connection request received
                # accept connection and update socket list
                accepted_socket, address = self._server_socket.accept()
                self._socket_list.append(accepted_socket)
            else:  # a message from a client, not a new connection
                try:
                    # receiving data from the socket.
                    data = current_socket.recv(RECV_BUFFER)
                    if data:
                        # if a socket is not added to list, then add it, otherwise data is an event
                        ip_sender = current_socket.getpeername()
                        if ip_sender not in self._ip_2_info:
                            data = json.loads(data)
                            self._ip_2_info.update({ip_sender: data})
                            self._name_2_ip.update({data['name']: ip_sender})
                            self._name_2_info.update({data['name']: data})
                            # print self._name_2_ip
                            # print self._ip_2_info
                            print self._name_2_info
                        else:

                            # ************************************ #
                            # ******BANG PROCESSES GO HERE******** #
                            # ************************************ #

                            self.process(data)

                            # ************************************ #
                            # **********END OF PROCESSES********** #
                            # ************************************ #

                except socket.error:
                    # recv method cannot be done means a socket is broken, so it has to be removed
                    current_socket.close()
                    ip_dis = current_socket.getpeername()
                    name_dis = self._ip_2_info[ip_dis]['name']
                    self._socket_list.remove(current_socket) if current_socket in self._socket_list else None
                    self._name_2_ip.pop(name_dis) if name_dis in self._name_2_ip else None
                    self._ip_2_info.pop(ip_dis) if ip_dis in self._ip_2_info else None
                    continue


class Players(Clients):

    def __init__(self, name, host, port):
        super(Players, self).__init__(host, port)
        self.name = name
        self.hit_points = 4
        self.cards = ['BANG', 'BANG', 'BEER', 'BEER']
        self._data_2_send = {'Sender': None, 'Action': None, 'Target': None}  # name only
        self._my_turn = False
        self._send_info()

    def _send_info(self):
        """at init, send all information about the player to server"""
        info = copy.copy(self)
        info.__dict__.pop('client_socket')
        info.__dict__.pop('_data_2_send')
        info = json.dumps(info.__dict__)
        self._send_msg(info)

    def bang(self, target):
        self.cards.remove('BANG')
        self._send_msg('BANG')
        return target

    def regen(self):
        self.hit_points += 1
        self.cards.remove('BEER')
        self._send_msg('BEER')

    def lose_hp(self):
        self.hit_points -= 1
