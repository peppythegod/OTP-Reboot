"""
 * Copyright (C) Caleb Marshall - All Rights Reserved
 * Written by Caleb Marshall <anythingtechpro@gmail.com>, August 17th, 2017
 * Contributed to by Prince Frizzy <theclashingfritz@gmail.com>, May 12th, 2018
 * Licensing information can found in 'LICENSE', which is part of this source code package.
"""

import collections
import time
import semidbm
import itertools
import inspect
import random
import threading

from panda3d.core import *
from panda3d.direct import *

from direct.distributed.PyDatagramIterator import PyDatagramIterator
from direct.distributed.PyDatagram import PyDatagram
from direct.distributed.MsgTypes import *
from direct.fsm.FSM import FSM

from realtime import io
from realtime import types
from realtime.notifier import notify
from realtime import util

from game.OtpDoGlobals import *
from game import ZoneUtil
from game.NameGenerator import NameGenerator
from game import genDNAFileName, extractGroupName
from game.dna.DNAParser import loadDNAFileAI, DNAStorage

ESSENTIAL_COMPLETE_ZONES = [OTP_ZONE_ID_OLD_QUIET_ZONE, 
    OTP_ZONE_ID_MANAGEMENT, 
    OTP_ZONE_ID_DISTRICTS,
    OTP_ZONE_ID_DISTRICTS_STATS,
    OTP_ZONE_ID_ELEMENTS
]

PERMA_ZONES = [OTP_ZONE_ID_OLD_QUIET_ZONE, OTP_ZONE_ID_DISTRICTS, OTP_ZONE_ID_DISTRICTS_STATS, OTP_ZONE_ID_MANAGEMENT]

class ClientOperation(FSM):
    notify = notify.new_category('ClientOperation')

    def __init__(self, manager, client, callback):
        FSM.__init__(self, self.__class__.__name__)

        self._manager = manager
        self._client = client
        self._callback = callback

    @property
    def manager(self):
        return self._manager

    @property
    def client(self):
        return self._client

    @property
    def callback(self):
        return self._callback

    @callback.setter
    def callback(self, callback):
        self._callback = callback

    def enterOff(self):
        pass

    def exitOff(self):
        pass

    def defaultFilter(self, request, *args):
        return FSM.defaultFilter(self, request, *args)

    def cleanup(self, success, *args, **kwargs):
        self.ignoreAll()
        self.manager.stop_operation(self.client)
        self.demand('Off')

        # only initiate callback if the cleanup was successful...
        if self._callback and success:
            self._callback(*args, **kwargs)

class ClientOperationManager(object):
    notify = notify.new_category('ClientOperationManager')

    def __init__(self, network):
        self._network = network
        self._channel2fsm = {}

    @property
    def network(self):
        return self._network

    @property
    def channel2fsm(self):
        return self._channel2fsm

    def has_fsm(self, channel):
        return channel in self._channel2fsm

    def add_fsm(self, channel, fsm):
        if self.has_fsm(channel):
            return

        self._channel2fsm[channel] = fsm

    def remove_fsm(self, channel):
        if not self.has_fsm(channel):
            return

        del self._channel2fsm[channel]

    def get_fsm(self, channel):
        return self._channel2fsm.get(channel)

    def run_operation(self, fsm, client, callback, *args, **kwargs):
        if self.has_fsm(client.allocated_channel):
            self.notify.warning('Cannot run operation: %s for channel %d, operation already running: %s!' % (
                fsm.__name__, client.allocated_channel, self.get_fsm(client.allocated_channel).__class__.__name__))

            return None

        operation = fsm(self, client, callback, *args, **kwargs)
        self.add_fsm(client.allocated_channel, operation)
        return operation

    def stop_operation(self, client):
        if not self.has_fsm(client.allocated_channel):
            self.notify.warning('Cannot stop operation for channel %d, unknown operation!' % (
                client.channel))

            return

        operation = self.get_fsm(client.allocated_channel)
        operation.demand('Off')

        self.remove_fsm(client.allocated_channel)

class LoadAccountFSM(ClientOperation):
    notify = notify.new_category('LoadAccountFSM')

    def __init__(self, manager, client, callback, play_token):
        ClientOperation.__init__(self, manager, client, callback)

        self._play_token = play_token
        self._account_id = None

    def enterStart(self):
        if self._play_token not in self.manager.dbm:
            self.demand('Create')
            return

        self._account_id = int(self.manager.dbm[self._play_token])
        self.manager.network.database_interface.query_object(self.client.channel,
            types.DATABASE_CHANNEL,
            self._account_id,
            self.__account_loaded,
            self.manager.network.dc_loader.dclasses_by_name['Account'])

    def __account_loaded(self, dclass, fields):
        if not dclass and not fields:
            self.notify.warning('Failed to load account: %d for channel: %d playtoken: %s!' % (
                self._account_id, self._client.channel, self._play_token))

            return

        self.request('SetAccount')

    def exitStart(self):
        pass

    def enterCreate(self):
        fields = {
            'ACCOUNT_AV_SET': ([0] * 6,),
            'BIRTH_DATE': ('',),
            'BLAST_NAME': (self._play_token,),
            'CREATED': (time.ctime(),),
            'FIRST_NAME': ('',),
            'LAST_LOGIN': ('',),
            'LAST_NAME': ('',),
            'PLAYED_MINUTES': ('',),
            'PLAYED_MINUTES_PERIOD': ('',),
            'HOUSE_ID_SET': ([0] * 6,),
            'ESTATE_ID': (0,)
        }

        self.manager.network.database_interface.create_object(self.client.channel,
            types.DATABASE_CHANNEL,
            self.manager.network.dc_loader.dclasses_by_name['Account'],
            fields=fields,
            callback=self.__account_created)

    def __account_created(self, account_id):
        self._account_id = account_id
        if not self._account_id:
            self.notify.warning('Failed to create account for channel: %d playtoken: %s!' % (
                self._client.channel, self._play_token))

            self.cleanup(False)
            return

        self.manager.dbm[self._play_token] = str(self._account_id)
        self.manager.dbm.sync()

        self.request('SetAccount')

    def exitCreate(self):
        pass

    def enterSetAccount(self):
        # the server says our login request was successful,
        # it is now ok to mark the client as authenticated...
        self._client.authenticated = True

        # add this connection to the account channel
        channel = self.client.get_account_connection_channel(self._account_id)
        self.client.register_for_channel(channel)

        # add them to the account channel
        channel = self._account_id << 32
        self.client.handle_set_channel_id(channel)

        # we're all done.
        self.cleanup(True)

    def exitSetAccount(self):
        pass

class ClientAvatarData(object):

    def __init__(self, do_id, name_list, dna, position, name_index):
        self._do_id = do_id
        self._name_list = name_list
        self._dna = dna
        self._position = position
        self._name_index = name_index

    @property
    def do_id(self):
        return self._do_id

    @do_id.setter
    def do_id(self, do_id):
        self._do_id = do_id

    @property
    def name_list(self):
        return self._name_list

    @name_list.setter
    def name_list(self, name_list):
        self._name_list = name_list

    @property
    def dna(self):
        return self._dna

    @dna.setter
    def dna(self, dna):
        self._dna = dna

    @property
    def position(self):
        return self._position

    @position.setter
    def position(self, position):
        self._position = position

    @property
    def name_index(self):
        return self._name_index

    @name_index.setter
    def name_index(self, name_index):
        self._name_index = name_index

class RetrieveAvatarsFSM(ClientOperation):
    notify = notify.new_category('RetrieveAvatarsFSM')

    def __init__(self, manager, client, callback, account_id):
        ClientOperation.__init__(self, manager, client, callback)

        self._account_id = account_id
        self._pending_avatars = []
        self._avatar_fields = {}

    def enterStart(self):
        self.manager.network.database_interface.query_object(self.client.channel,
            types.DATABASE_CHANNEL,
            self._account_id,
            self.__account_loaded,
            self.manager.network.dc_loader.dclasses_by_name['Account'])

    def exitStart(self):
        pass

    def __account_loaded(self, dclass, fields):
        avatar_list = fields['ACCOUNT_AV_SET'][0]
        for avatar_id in avatar_list:
            if not avatar_id:
                continue

            self._pending_avatars.append(avatar_id)

            def response(dclass, fields, avatar_id=avatar_id):
                self._avatar_fields[avatar_id] = fields
                self._pending_avatars.remove(avatar_id)
                if not self._pending_avatars:
                    self.request('SetAvatars')

            self.manager.network.database_interface.query_object(self.client.channel,
                types.DATABASE_CHANNEL,
                avatar_id,
                response,
                self.manager.network.dc_loader.dclasses_by_name['DistributedToon'])

        if not self._pending_avatars:
            self.request('SetAvatars')

    def enterSetAvatars(self):
        avatar_list = []

        for avatar_id, fields in self._avatar_fields.items():
            avatar_data = ClientAvatarData(avatar_id, [fields['setName'][0], '', '', ''], fields['setDNAString'][0],
                fields['setPosIndex'][0], 0)

            avatar_list.append(avatar_data)

        # we're all done.
        self.cleanup(True, avatar_list)

    def exitSetAvatars(self):
        pass

class CreateAvatarFSM(ClientOperation):
    notify = notify.new_category('CreateAvatarFSM')

    def __init__(self, manager, client, callback, echo_context, account_id, dna_string, index):
        ClientOperation.__init__(self, manager, client, callback)

        self._account_id = account_id
        self._dna_string = dna_string
        self._callback = callback
        self._echo_context = echo_context
        self._index = index

    def enterStart(self):
        fields = {
            'setDNAString': (self._dna_string,),
            'setPosIndex': (self._index,),
            'setName': ('Toon',)
        }

        self.manager.network.database_interface.create_object(self.client.channel,
            types.DATABASE_CHANNEL,
            self.manager.network.dc_loader.dclasses_by_name['DistributedToon'],
            fields=fields,
            callback=lambda avatar_id: self.__avatar_created(avatar_id, self._index))

    def __avatar_created(self, avatar_id, index):
        self.manager.network.database_interface.query_object(self.client.channel,
            types.DATABASE_CHANNEL,
            self._account_id,
            lambda dclass, fields: self.__account_loaded(dclass, fields, avatar_id, index),
            self.manager.network.dc_loader.dclasses_by_name['Account'])

    def __account_loaded(self, dclass, fields, avatar_id, index):
        avatar_list = fields['ACCOUNT_AV_SET'][0]
        avatar_list[index] = avatar_id

        new_fields = {
            'ACCOUNT_AV_SET': (avatar_list,)
        }

        self.manager.network.database_interface.update_object(self.client.channel,
            types.DATABASE_CHANNEL,
            self._account_id,
            self.manager.network.dc_loader.dclasses_by_name['Account'],
            new_fields)

        # We're all done
        self.cleanup(True, self._echo_context, avatar_id)

    def exitStart(self):
        pass

class LoadAvatarFSM(ClientOperation):
    notify = notify.new_category('LoadAvatarFSM')

    def __init__(self, manager, client, callback, account_id, avatar_id):
        ClientOperation.__init__(self, manager, client, callback)

        self._account_id = account_id
        self._avatar_id = avatar_id

        self._dc_class = None
        self._fields = {}

    def enterStart(self):

        def response(dclass, fields):
            self._dc_class = dclass
            self._fields = fields
            self.request('Activate')

        self.manager.network.database_interface.query_object(self.client.channel,
            types.DATABASE_CHANNEL,
            self._avatar_id,
            response,
            self.manager.network.dc_loader.dclasses_by_name['DistributedToon'])

    def exitStart(self):
        pass

    def enterActivate(self):
        # add them to the avatar channel
        channel = self.client.get_puppet_connection_channel(self._avatar_id)
        self.client.register_for_channel(channel)

        # set their sender channel to represent their account affiliation
        channel = self._account_id << 32 | self._avatar_id
        self.client.handle_set_channel_id(channel)

        datagram = io.NetworkDatagram()
        datagram.add_header(types.STATESERVER_CHANNEL, channel,
            types.STATESERVER_OBJECT_GENERATE_WITH_REQUIRED_OTHER)

        datagram.add_uint32(self._avatar_id)
        datagram.add_uint32(0)
        datagram.add_uint32(0)
        datagram.add_uint16(self._dc_class.get_number())

        sorted_fields = {}
        for field_name, field_args in self._fields.items():
            field = self._dc_class.get_field_by_name(field_name)

            if not field:
                self.notify.warning('Failed to pack fields for object %d, unknown field: %s!' % (
                    self._avatar_id, field_name))

                return

            sorted_fields[field.get_number()] = field_args

        sorted_fields = collections.OrderedDict(sorted(
            sorted_fields.items()))

        field_packer = DCPacker()
        for field_index, field_args in sorted_fields.items():
            field = self._dc_class.get_field_by_index(field_index)

            if not field:
                self.notify.error('Failed to pack required field: %d for object %d, unknown field!' % (
                    field_index, self._avatar_id))

            field_packer.begin_pack(field)
            field.pack_args(field_packer, field_args)
            field_packer.end_pack()

        datagram.append_data(field_packer.get_string())

        other_fields = {
            'setCommonChatFlags': (self._fields.get('setCommonChatFlags', 0),),
            'setTrophyScore': (self._fields.get('setTrophyScore', 0),),
        }

        field_packer = DCPacker()
        for field_name, field_args in other_fields.items():
            field = self._dc_class.get_field_by_name(field_name)

            if not field:
                self.notify.error('Failed to pack other field: %s for object %d, unknown field!' % (
                    field_name, self._avatar_id))

            field_packer.raw_pack_uint16(field.get_number())
            field_packer.begin_pack(field)
            field.pack_args(field_packer, field_args)
            field_packer.end_pack()

        datagram.add_uint16(len(other_fields))
        datagram.append_data(field_packer.get_string())
        self.manager.network.handle_send_connection_datagram(datagram)

        # grant ownership over the distributed object...
        datagram = io.NetworkDatagram()
        datagram.add_header(self._avatar_id, channel,
            types.STATESERVER_OBJECT_SET_OWNER)

        datagram.add_uint64(channel)
        self.manager.network.handle_send_connection_datagram(datagram)

        # setup a post remove message that will delete the
        # client's toon object when they disconnect...
        post_remove = io.NetworkDatagram()
        post_remove.add_header(self._avatar_id, channel,
            types.STATESERVER_OBJECT_DELETE_RAM)

        post_remove.add_uint32(self._avatar_id)

        datagram = io.NetworkDatagram()
        datagram.add_control_header(self.client.allocated_channel,
            types.CONTROL_ADD_POST_REMOVE)

        datagram.append_data(post_remove.get_message())
        self.manager.network.handle_send_connection_datagram(datagram)

        # we're all done.
        self.cleanup(True, self._avatar_id)

    def exitActivate(self):
        pass

class LoadFriendsListFSM(ClientOperation):
    notify = notify.new_category('LoadAvatarFSM')

    def __init__(self, manager, client, callback, account_id, avatar_id):
        ClientOperation.__init__(self, manager, client, callback)

        self._account_id = account_id
        self._avatar_id = avatar_id

        self._dc_class = None
        self._fields = {}

        self._friends_list = {}
        self._pending_friends = []

    def enterStart(self):

        def response(dclass, fields):
            self._dc_class = dclass
            self._fields = fields
            self.request('QueryFriends')

        self.manager.network.database_interface.query_object(self.client.channel,
            types.DATABASE_CHANNEL,
            self._avatar_id,
            response,
            self.manager.network.dc_loader.dclasses_by_name['DistributedToon'])

    def exitStart(self):
        pass

    def enterQueryFriends(self):
        friends_list, = self._fields['setFriendsList']
        if not friends_list:
            self.cleanup(False)
            return

        self._pending_friends = {friend_id: friend_type for friend_id, friend_type in friends_list}
        for friend_id, friend_type in friends_list:

            def queryFriendCallback(dclass, fields, avatar_id=friend_id):
                self._friends_list[avatar_id] = [dclass, fields]
                del self._pending_friends[avatar_id]

                if not self._pending_friends:
                    self.request('LoadFriends')

            self.manager.network.database_interface.query_object(self.client.channel,
                types.DATABASE_CHANNEL,
                friend_id,
                queryFriendCallback,
                self.manager.network.dc_loader.dclasses_by_name['DistributedToon'])

    def exitQueryFriends(self):
        pass

    def enterLoadFriends(self):
        our_channel = self.client.get_puppet_connection_channel(self._avatar_id)
        for friend_id in self._friends_list:
            friend_channel = self.client.get_puppet_connection_channel(friend_id)
            friend_online = self.manager.network.get_handler_from_channel(friend_channel) is not None

            # tell us if they are online or not...
            datagram = io.NetworkDatagram()

            if friend_online:
                datagram.add_uint16(types.CLIENT_FRIEND_ONLINE)
            else:
                datagram.add_uint16(types.CLIENT_FRIEND_OFFLINE)

            datagram.add_uint32(friend_id)
            self.client.handle_send_datagram(datagram)

            # tell them that we are online if they are online...
            if friend_online:
                datagram = io.NetworkDatagram()
                datagram.add_header(friend_channel, our_channel,
                    types.CLIENTAGENT_FRIEND_ONLINE)

                datagram.add_uint32(self._avatar_id)
                self.manager.network.handle_send_connection_datagram(datagram)

            # setup a post remove that will tell all of our friends
            # that we are offline when we disconnect...
            post_remove = io.NetworkDatagram()
            post_remove.add_header(friend_channel, our_channel,
                types.CLIENTAGENT_FRIEND_OFFLINE)

            post_remove.add_uint32(self._avatar_id)

            datagram = io.NetworkDatagram()
            datagram.add_control_header(self.client.allocated_channel,
                types.CONTROL_ADD_POST_REMOVE)

            datagram.append_data(post_remove.get_message())
            self.manager.network.handle_send_connection_datagram(datagram)

        datagram = io.NetworkDatagram()
        datagram.add_uint16(types.CLIENT_GET_FRIEND_LIST_RESP)
        datagram.add_uint8(0)
        datagram.add_uint16(len(self._friends_list))

        for friend_id in self._friends_list:
            dclass, fields = self._friends_list[friend_id]

            datagram.add_uint32(friend_id)
            datagram.add_string(fields['setName'][0])
            datagram.add_string(fields['setDNAString'][0])

        self.client.handle_send_datagram(datagram)

        # we're all done.
        self.cleanup(True)

    def exitLoadFriends(self):
        pass

class SetNameFSM(ClientOperation):
    notify = notify.new_category('SetNameFSM')

    def __init__(self, manager, client, callback, avatar_id, wish_name):
        self.notify.debug("SetNameFSM.__init__(%s, %s, %s, %s, %s)" % (str(manager), str(client),
            str(callback), str(avatar_id), str(wish_name)))

        ClientOperation.__init__(self, manager, client, callback)

        self._avatar_id = avatar_id
        self._wish_name = wish_name
        self._callback = callback
        self._dc_class = None
        self._fields = {}

    def enterStart(self):
        self.notify.debug("SetNameFSM.enterQuery()")

        def response(dclass, fields):
            self.notify.debug("SetNameFSM.enterQuery.response(%s, %s)" % (str(dclass), str(fields)))
            self._dc_class = dclass
            self._fields = fields
            self.request('SetName')

        self.manager.network.database_interface.query_object(self.client.channel,
            types.DATABASE_CHANNEL,
            self._avatar_id,
            response,
            self.manager.network.dc_loader.dclasses_by_name['DistributedToon'])

    def exitStart(self):
        self.notify.debug("SetNameFSM.exitQuery()")

    def enterSetName(self):
        self.notify.debug("SetNameFSM.enterSetName()")

        # TODO: Parse a check the wish-name for bad names and etc.
        new_fields = {
             'setName': (self._wish_name,)
        }

        #self.notify.warning("New fields are \n%s" % (str(self._fields)))

        self.manager.network.database_interface.update_object(self.client.channel,
            types.DATABASE_CHANNEL,
            self._avatar_id,
            self.manager.network.dc_loader.dclasses_by_name['DistributedToon'],
            new_fields)

        # We're all done
        self.cleanup(True, self._avatar_id, self._wish_name)

    def exitSetName(self):
        self.notify.debug("SetNameFSM.exitSetName()")

class GetAvatarDetailsFSM(ClientOperation):
    notify = notify.new_category('GetAvatarDetailsFSM')

    def __init__(self, manager, client, callback, avatar_id):
        ClientOperation.__init__(self, manager, client, callback)

        self._avatar_id = avatar_id
        self._callback = callback
        self._dc_class = None
        self._fields = {}

    def enterStart(self):

        def response(dclass, fields):
            self._dc_class = dclass
            self._fields = fields
            self.request('SendDetails')

        self.manager.network.database_interface.query_object(self.client.channel,
            types.DATABASE_CHANNEL,
            self._avatar_id,
            response,
            self.manager.network.dc_loader.dclasses_by_name['DistributedToon'])

    def exitStart(self):
        pass

    def enterSendDetails(self):
        datagram = PyDatagram()
        datagram.add_uint64(self._avatar_id)
        datagram.add_uint64(0)
        datagram.add_uint32(0)
        datagram.add_uint16(0)

        sorted_fields = {}
        for field_name, field_args in self._fields.items():
            field = self._dc_class.get_field_by_name(field_name)
            if not field:
                self.notify.warning('Failed to pack fields for object %d, unknown field: %s!' % (
                    self._avatar_id, field_name))

                self.cleanup(False)
                return

            sorted_fields[field.get_number()] = field_args

        sorted_fields = collections.OrderedDict(sorted(
            sorted_fields.items()))

        field_packer = DCPacker()
        for field_index, field_args in sorted_fields.items():
            field = self._dc_class.get_field_by_index(field_index)
            if not field:
                self.notify.warning('Failed to pack required field: %d for object %d, unknown field!' % (
                    field_index, self._avatar_id))

                self.cleanup(False)
                return

            field_packer.begin_pack(field)
            field.pack_args(field_packer, field_args)
            field_packer.end_pack()

        datagram.append_data(field_packer.get_string())
        di = PyDatagramIterator(datagram)

        # We're all done
        self.cleanup(True, False, di)

    def exitSendDetails(self):
        pass

class DeleteAvatarFSM(ClientOperation):
    notify = notify.new_category('DeleteAvatarFSM')

    def __init__(self, manager, client, callback, account_id, avatar_id):
        ClientOperation.__init__(self, manager, client, callback)

        self._account_id = account_id
        self._avatar_id = avatar_id
        self._pending_avatars = []
        self._avatar_fields = {}

    def enterStart(self):
        self.manager.network.database_interface.query_object(self.client.channel,
            types.DATABASE_CHANNEL,
            self._account_id,
            self.__account_loaded,
            self.manager.network.dc_loader.dclasses_by_name['Account'])

    def exitStart(self):
        pass

    def __account_loaded(self, dclass, fields):
        self.avatar_list = fields['ACCOUNT_AV_SET'][0]
        for avatar_id in self.avatar_list:
            if not avatar_id or avatar_id == self._avatar_id:
                continue

            self._pending_avatars.append(avatar_id)

            def response(dclass, fields, avatar_id=avatar_id):
                self._avatar_fields[avatar_id] = fields
                self._pending_avatars.remove(avatar_id)
                if not self._pending_avatars:
                    self.request('ApplyAvatars')

            self.manager.network.database_interface.query_object(self.client.channel,
                types.DATABASE_CHANNEL,
                avatar_id,
                response,
                self.manager.network.dc_loader.dclasses_by_name['DistributedToon'])

        if not self._pending_avatars:
            self.request('ApplyAvatars')

    def enterApplyAvatars(self):
        for avatar_id in self.avatar_list:
            if avatar_id == self._avatar_id:
                index = self.avatar_list.index(self._avatar_id)
                self.avatar_list[index] = 0
                break

        new_fields = {
            'ACCOUNT_AV_SET': (self.avatar_list,)
        }

        def update_callback(fields):
            if fields is not None:
                self.cleanup(False)
                return

            self.demand('SetAvatars')

        self.manager.network.database_interface.update_object(self.client.channel,
            types.DATABASE_CHANNEL,
            self._account_id,
            self.manager.network.dc_loader.dclasses_by_name['Account'],
            new_fields,
            callback=update_callback)

        del self.avatar_list

    def exitApplyAvatars(self):
        pass

    def enterSetAvatars(self):
        avatar_list = []
        for avatar_id, fields in self._avatar_fields.items():
            avatar_data = ClientAvatarData(avatar_id, [fields['setName'][0], '', '', ''], fields['setDNAString'][0],
                fields['setPosIndex'][0], 0)

            avatar_list.append(avatar_data)

        # we're all done.
        self.cleanup(True, avatar_list)

    def exitSetAvatars(self):
        pass
        
class SetAvatarZonesFSM(ClientOperation):
    notify = notify.new_category('SetAvatarZonesFSM')

    def __init__(self, manager, client, callback, avatar_id, zone_id):
        self.notify.debug("SetAvatarZonesFSM.__init__(%s, %s, %s, %s, %s)" % (str(manager), str(client),
            str(callback), str(avatar_id), str(zone_id)))

        ClientOperation.__init__(self, manager, client, callback)

        self._avatar_id = avatar_id
        self._callback = callback
        self._dc_class = None
        self._zone_id = zone_id
        self._fields = {}

    def enterStart(self):
        self.notify.debug("SetAvatarZonesFSM.enterQuery()")

        def response(dclass, fields):
            self.notify.debug("SetAvatarZonesFSM.enterQuery.response(%s, %s)" % (str(dclass), str(fields)))
            self._dc_class = dclass
            self._fields = fields
            self.request('SetField')

        self.manager.network.database_interface.query_object(self.client.channel,
            types.DATABASE_CHANNEL,
            self._avatar_id,
            response,
            self.manager.network.dc_loader.dclasses_by_name['DistributedToon'])

    def exitStart(self):
        self.notify.debug("SetAvatarZonesFSM.exitQuery()")

    def enterSetField(self):
        self.notify.debug("SetAvatarZonesFSM.enterSetField()")

        hoodsVisited = self._fields['setHoodsVisited'][0]
        if self._zone_id not in hoodsVisited:
            hoodsVisited.append(self._zone_id)
            
        # For some reason we can't update more than one field at once?
            
        new_fields = {
             'setHoodsVisited': (hoodsVisited,)
        }

        self.manager.network.database_interface.update_object(self.client.channel,
            types.DATABASE_CHANNEL,
            self._avatar_id,
            self.manager.network.dc_loader.dclasses_by_name['DistributedToon'],
            new_fields)
            
        new_fields = {
             'setLastHood': (self._zone_id,)
        }

        self.manager.network.database_interface.update_object(self.client.channel,
            types.DATABASE_CHANNEL,
            self._avatar_id,
            self.manager.network.dc_loader.dclasses_by_name['DistributedToon'],
            new_fields)
            
        new_fields = {
             'setDefaultZone': (self._zone_id,)
        }

        self.manager.network.database_interface.update_object(self.client.channel,
            types.DATABASE_CHANNEL,
            self._avatar_id,
            self.manager.network.dc_loader.dclasses_by_name['DistributedToon'],
            new_fields)

        # We're all done
        self.cleanup(True)

    def exitSetField(self):
        self.notify.debug("SetAvatarZonesFSM.exitSetField()")

class SetNamePatternFSM(ClientOperation):
    notify = notify.new_category('SetNamePatternFSM')

    def __init__(self, manager, client, callback, avatar_id, pattern):
        self.notify.debug("SetNamePatternFSM.__init__(%s, %s, %s, %s, %s)" % (str(manager), str(client),
            str(callback), str(avatar_id), str(pattern)))

        ClientOperation.__init__(self, manager, client, callback)

        self._avatar_id = avatar_id
        self._pattern = pattern
        self._callback = callback
        self._dc_class = None
        self._fields = {}

    def enterStart(self):
        self.notify.debug("SetNamePatternFSM.enterQuery()")

        def response(dclass, fields):
            self.notify.debug("SetNamePatternFSM.enterQuery.response(%s, %s)" % (str(dclass), str(fields)))

            self._dc_class = dclass
            self._fields = fields
            self.request('SetPatternName')

        self.manager.network.database_interface.query_object(self.client.channel,
            types.DATABASE_CHANNEL,
            self._avatar_id,
            response,
            self.manager.network.dc_loader.dclasses_by_name['DistributedToon'])

    def exitStart(self):
        self.notify.debug("SetNamePatternFSM.exitQuery()")

    def enterSetPatternName(self):
        self.notify.debug("SetNamePatternFSM.enterSetPatternName()")

        nameGenerator = NameGenerator()

        # Render the pattern into a string:
        parts = []
        for p, f in self._pattern:
            part = nameGenerator.nameDictionary.get(p, ('', ''))[1]
            if f:
                part = part[:1].upper() + part[1:]
            else:
                part = part.lower()

            parts.append(part)

        # Merge 2&3 (the last name) as there should be no space:
        parts[2] += parts.pop(3)
        while '' in parts:
            parts.remove('')

        name = ' '.join(parts)
        del nameGenerator

        new_fields = {
             'setName': (name,)
        }

        #self.notify.warning("New fields are \n%s" % (str(self._fields)))

        self.manager.network.database_interface.update_object(self.client.channel,
            types.DATABASE_CHANNEL,
            self._avatar_id,
            self.manager.network.dc_loader.dclasses_by_name['DistributedToon'],
            new_fields)

        # We're all done
        self.cleanup(True, self._avatar_id)

    def exitSetPatternName(self):
        self.notify.debug("SetNamePatternFSM.exitSetPatternName()")

class ClientAccountManager(ClientOperationManager):
    notify = notify.new_category('ClientAccountManager')

    def __init__(self, *args, **kwargs):
        ClientOperationManager.__init__(self, *args, **kwargs)

        self._dbm = semidbm.open(config.GetString('clientagent-dbm-filename', 'databases/database.dbm'),
            config.GetString('clientagent-dbm-mode', 'c'))

    @property
    def dbm(self):
        return self._dbm

    def handle_operation(self, operationFSM, client, callback, *args, **kwargs):
        operation = self.run_operation(operationFSM, client, callback, *args, **kwargs)
        if not operation:
            self.notify.warning('Failed to handle unknown operation: %r!' % operationFSM)
            return

        operation.request('Start')

class InterestManager(object):

    def __init__(self):
        self._interest_zones = []
        self._interest_objects = []

    @property
    def interest_zones(self):
        return self._interest_zones

    def has_interest_zone(self, zone_id):
        return zone_id in self._interest_zones

    def add_interest_zone(self, zone_id):
        if zone_id in self._interest_zones:
            return

        self._interest_zones.append(zone_id)

    def remove_interest_zone(self, zone_id):
        if zone_id not in self._interest_zones:
            return

        self._interest_zones.remove(zone_id)

    def clear(self):
        self._interest_zones = []
        
    def add_interest_object(self, i):
        self._interest_objects.append(i)
        
    def has_interest_object(self, i):
        return i in self._interest_objects
        
    def has_interest_object_id(self, _id, _obj = False):
        for interest in self._interest_objects:
            if interest.getId() == _id:
                if _obj:
                    return interest
                    
                return True
                
        return False
        
    def has_interest_object_parent(self, parentId):
        for interest in self._interest_objects:
            if interest.getParent() == parentId:
                return True
                
        return False
        
    def has_interest_object_zone(self, zoneId):
        for interest in self._interest_objects:
            if interest.hasZone(zoneId) or interest.hasView(zoneId):
                return True
                
        return False
        
    def has_interest_object_parent_and_zone(self, parentId, zoneId, getObj = False, includeViews = False):
        for interest in self._interest_objects:
            if interest.getParent() == parentId and (interest.hasZone(zoneId) or (includeViews and interest.hasView(zoneId))):
                if getObj:
                    return interest
                return True
                
        return False
        
    def get_interest_object_by_id(self, _id):
        return self.has_interest_object_id(_id, True)
        
    def remove_interest_object(self, i):
        self._interest_objects.remove(i)
        
    def get_interest_objects(self):
        return self._interest_objects
        
class InterestOperation:
    def __init__(self, client, timeout, Id, context, 
            parent, zones, caller):
            
        self.client = client
        self.timeout = timeout
        self.id = Id
        self.context = context
        self.parent = parent
        self.zones = zones
        self.caller = caller
        
class ZoneList:
    
    def __init__(self):
        self.zones = []
    
    def addZone(self, zoneId):
        self.zones.append(zoneId)
        
    def removeZone(self, zoneId):
        self.zones.remove(zoneId)
        
    def getZones(self):
        return self.zones
        
    def hasZone(self, zoneId):
        return zoneId in self.zones
        
class Interest:
    
    def __init__(self):
        self.zones = ZoneList()
        self.vis_zones = set()
        self.id = -1
        self.context = -1
        self.parent = -1
    
    def setId(self, _id):
        self.id = _id
        
    def getId(self):
        return self.id
        
    def setContext(self, _context):
        self.context = _context
        
    def getContext(self):
        return self.context
        
    def setParent(self, _parent):
        self.parent = _parent
        
    def getParent(self):
        return self.parent
        
    def addZone(self, zone):
        self.zones.addZone(zone)
        
    def removeZone(self, zone):
        self.zones.removeZone(zone)
        
    def getZones(self):
        return self.zones.getZones()
        
    def hasZone(self, zone):
        return self.zones.hasZone(zone)
        
    def setVisZones(self, zones):
        self.vis_zones = zones
        
    def getVisZones(self):
        return self.vis_zones
        
    def hasView(self, zone):
        return zone in self.vis_zones
        
class VisibleObject:
    def __init__(self):
        self.parent = -1
        self.zone = -1
        self.id = -1
    
    def setParent(self, parent):
        self.parent = parent
        
    def getParent(self):
        return self.parent
        
    def setZone(self, zone):
        self.zone = zone
        
    def getZone(self):
        return self.zone
        
    def setId(self, _id):
        self.id = id
        
    def getId(self):
        return self.id

class Client(io.NetworkHandler):
    notify = notify.new_category('Client')

    def __init__(self, *args, **kwargs):
        io.NetworkHandler.__init__(self, *args, **kwargs)

        self.channel = self.network.channel_allocator.allocate()
        self._authenticated = False

        self._interest_manager = InterestManager()
        self._deferred_callback = None

        self._seen_objects = {}
        self._owned_objects = []
        self._pending_objects = []
        
        # 2010
        self._visibile_objects = []
        self._seen_objects_2 = []
        self._pending_interests = {}
        self._context_id = 0
        self._context_to_callback = {}
        self._interest_delete_queue = []
        
        #! This is meant to be a temporary hacky way to get streets working properly!
        self._street_zones = (2100, 2200, 2300, 1100, 1200, 1300, 3100, 3200, 3300, 4100, 4200, 4300, 5100, 5200, 5300, 9100, 9200)
        self._forced_zones = {}
        
        self._dna_stores = {}
        
        self.idtest = random.random()

    @property
    def authenticated(self):
        return self._authenticated

    @authenticated.setter
    def authenticated(self, authenticated):
        self._authenticated = authenticated
        
    def get_next_context(self):
        self._context_id += 1
        return self._context_id

    def has_seen_object(self, do_id, erase = False):
        for zone_id, seen_objects in list(self._seen_objects.items()):
            if do_id in seen_objects:
                if erase:
                    self._seen_objects[zone_id].remove(do_id)
                return True

        return False

    def startup(self):
        io.NetworkHandler.startup(self)

    def handle_send_disconnect(self, code, reason):
        self.notify.warning('Disconnecting channel: %d, reason: %s' % (
            self.channel, reason))

        datagram = io.NetworkDatagram()
        datagram.add_uint16(types.CLIENT_GO_GET_LOST)
        datagram.add_uint16(code)
        datagram.add_string(reason)

        self.handle_send_datagram(datagram)
        self.handle_disconnect()

    def handle_datagram(self, di):
        try:
            message_type = di.get_uint16()
        except:
            self.handle_send_disconnect(types.CLIENT_DISCONNECT_TRUNCATED_DATAGRAM,
                'Received truncated datagram from channel: %d!' % (
                    self._channel))

            return

        if message_type == types.CLIENT_HEARTBEAT:
            pass
        elif message_type == types.CLIENT_LOGIN_2 or message_type == 125: #125 == CLIENT_LOGIN_TOONTOWN
            self.handle_login(di, message_type == 125)
        elif message_type == types.CLIENT_DISCONNECT:
            self.handle_disconnect()
        else:
            if not self._authenticated:
                self.handle_send_disconnect(types.CLIENT_DISCONNECT_ANONYMOUS_VIOLATION,
                    'Cannot send datagram with message type: %d, channel: %d not yet authenticated!' % (
                        message_type, self.channel))

                return
            else:
                self.handle_authenticated_datagram(message_type, di)

    def handle_authenticated_datagram(self, message_type, di):
        if message_type == types.CLIENT_GET_SHARD_LIST:
            self.handle_get_shard_list()
        elif message_type == types.CLIENT_GET_AVATARS:
            self.handle_get_avatars()
        elif message_type == types.CLIENT_GET_AVATAR_DETAILS:
            self.handle_get_avatar_details(di)
        elif message_type == types.CLIENT_CREATE_AVATAR:
            self.handle_create_avatar(di)
        elif message_type == types.CLIENT_SET_AVATAR:
            self.handle_set_avatar(di)
        elif message_type == types.CLIENT_SET_WISHNAME:
            self.handle_set_wishname(di)
        elif message_type == types.CLIENT_SET_NAME_PATTERN:
            self.handle_set_name_pattern(di)
        elif message_type == types.CLIENT_DELETE_AVATAR:
            self.handle_delete_avatar(di)
        elif message_type == types.CLIENT_GET_FRIEND_LIST:
            self.handle_get_friends_list(di)
        elif message_type == types.CLIENT_REMOVE_FRIEND:
            pass
        elif message_type == types.CLIENT_SET_SHARD:
            self.handle_set_shard(di)
        elif message_type == types.CLIENT_SET_ZONE:
            self.handle_set_zone(di)
        elif message_type == types.CLIENT_OBJECT_UPDATE_FIELD:
            self.handle_object_update_field(di)
        elif message_type == types.CLIENT_ADD_INTEREST:
            self.handle_add_interest(di)
        elif message_type == types.CLIENT_REMOVE_INTEREST:
            self.handle_remove_interest(di)
        elif message_type == types.CLIENT_OBJECT_LOCATION:
            self.handle_client_object_location(di)
        else:
            self.handle_send_disconnect(types.CLIENT_DISCONNECT_INVALID_MSGTYPE,
                'Unknown datagram: %d from channel: %d!' % (
                    message_type, self.channel))

            return

    def handle_internal_datagram(self, message_type, sender, di):
        if message_type == types.CLIENTAGENT_DISCONNECT:
            self.handle_send_disconnect(di.get_uint16(), di.get_string())
        elif message_type == types.CLIENTAGENT_FRIEND_ONLINE:
            self.handle_friend_online(di)
        elif message_type == types.CLIENTAGENT_FRIEND_OFFLINE:
            self.handle_friend_offline(di)
        elif message_type == types.STATESERVER_GET_SHARD_ALL_RESP:
            self.handle_get_shard_list_resp(di)
        elif message_type == types.STATESERVER_OBJECT_LOCATION_ACK:
            self.handle_object_location_ack(di)
        elif message_type == types.STATESERVER_OBJECT_GET_ZONES_OBJECTS_RESP:
            self.handle_object_get_zones_objects_resp(di)
        elif message_type == types.STATESERVER_OBJECT_GET_ZONES_OBJECTS_2_RESP:
            self.handle_object_get_zones_objects_resp_2(di)
        elif message_type == types.STATESERVER_OBJECT_ENTER_OWNER_WITH_REQUIRED:
            self.handle_object_enter_owner(False, di)
        elif message_type == types.STATESERVER_OBJECT_ENTER_OWNER_WITH_REQUIRED_OTHER:
            self.handle_object_enter_owner(True, di)
        elif message_type == types.STATESERVER_OBJECT_ENTER_LOCATION_WITH_REQUIRED:
            self.handle_object_enter_location(False, di)
        elif message_type == types.STATESERVER_OBJECT_ENTER_LOCATION_WITH_REQUIRED_OTHER:
            self.handle_object_enter_location(True, di)
        elif message_type == types.STATESERVER_OBJECT_DELETE_RAM:
            self.handle_object_delete_ram(di)
        elif message_type == types.STATESERVER_OBJECT_UPDATE_FIELD:
            self.handle_object_update_field_resp(sender, di)
        else:
            self.network.database_interface.handle_datagram(message_type, di)
            
    def handle_client_object_location(self, di):
        try:
            doId = di.get_uint32()
            parentId = di.get_uint32()
            zoneId = di.get_uint32()
        except:
            self.handle_send_disconnect(types.CLIENT_DISCONNECT_TRUNCATED_DATAGRAM,
                'Received truncated datagram from channel: %d!' % (
                    self._channel))
            return
           
        context = self.get_next_context()
        
        _deferred_callback = util.DeferredCallback(self.handle_set_loc_shard_callback, zoneId)
        self._context_to_callback[context] = _deferred_callback
        
        datagram = io.NetworkDatagram()
        datagram.add_header(doId, self.channel,
            types.STATESERVER_OBJECT_SET_AI)
        
        datagram.add_uint64(parentId - 1)
        datagram.add_uint32(context)
        datagram.add_uint32(zoneId)
        self.network.handle_send_connection_datagram(datagram)

    def handle_set_loc_shard_callback(self, do_id, old_parent_id, old_zone_id, new_parent_id, new_zone_id, actualZone = None):
        return
            
    def handle_remove_interest(self, di):
        try:
            interestId = di.getUint16()
        except:
            self.handle_send_disconnect(types.CLIENT_DISCONNECT_TRUNCATED_DATAGRAM,
                'Received truncated datagram from channel: %d!' % (
                    self._channel))
            return
            
        old_vis_zones = set()
        kill_zones = []
        if self._interest_manager.has_interest_object_id(interestId):
            interest = self._interest_manager.get_interest_object_by_id(interestId)
                            
            for zone in interest.getZones():
                if len(self.lookup_interest(interest.getParent(), zone)) == 1:
                    kill_zones.append(zone)
                        
                    old_zone_id = zone
                    old_zone_in_street_branch = self.get_in_street_branch(old_zone_id)
                    if old_zone_in_street_branch:
                        old_branch_zone_id = ZoneUtil.getBranchZone(old_zone_id)
                        if old_zone_id % 100 != 0:
                            old_vis_zones.update(self.get_vis_branch_zones(old_zone_id))
                            for zone_id in old_vis_zones:
                                print "0 VIS KILL, ", zone_id
                                kill_zones.append(zone_id)
                        del self._dna_stores[old_branch_zone_id]
            
            self.close_zones(kill_zones, interest.getParent())
            self.handle_interest_done(interest.getId(), interest.getContext())
            self._interest_manager.remove_interest_object(interest)
        else:
            self.notify.info("Delete for unknown interest id %d" %interestId)
            
    def get_in_street_branch(self, zone_id):
        if not ZoneUtil.isPlayground(zone_id):
            where = ZoneUtil.getWhereName(zone_id, True)
            return where == 'street'

        return False
        
    def get_vis_branch_zones(self, zone_id):
        branch_zone_id = ZoneUtil.getBranchZone(zone_id)
        dnaStore = self._dna_stores.get(branch_zone_id)
        if not dnaStore:
            dnaStore = DNAStorage()
            dnaFileName = genDNAFileName(branch_zone_id)
            loadDNAFileAI(dnaStore, dnaFileName, None)
            self._dna_stores[branch_zone_id] = dnaStore

        zoneVisDict = {}
        for i in xrange(dnaStore.getNumDNAVisGroupsAI()):
            groupFullName = dnaStore.getDNAVisGroupName(i)
            visGroup = dnaStore.getDNAVisGroupAI(i)
            visZoneId = int(extractGroupName(groupFullName))
            visZoneId = ZoneUtil.getTrueZoneId(visZoneId, zone_id)
            visibles = []
            for i in xrange(visGroup.getNumVisibles()):
                visibles.append(int(visGroup.visibles[i]))

            visibles.append(ZoneUtil.getBranchZone(visZoneId))
            zoneVisDict[visZoneId] = visibles

        return zoneVisDict[zone_id]
            
    def handle_add_interest(self, di): 
        try:
            interest = self.build_interest(di)
        except:
            self.handle_send_disconnect(types.CLIENT_DISCONNECT_TRUNCATED_DATAGRAM,
                'Received truncated datagram from channel: %d!' % (
                    self._channel))
            return
        print "============="
        newZones = []
        for zone in interest.getZones():
            if not self._interest_manager.has_interest_object_parent_and_zone(interest.getParent(), zone):
                newZones.append(zone)
            else:
                if len(interest.getZones()) == 1:
                    # This interest was already created and letting it go through empty would erase previous interest zones
                    print "saving interest"
                    self.handle_interest_done(interest.getId(), interest.getContext())
                    return
                
        new_vis_zones = set()
        for new_zone_id in newZones:
            print "searching vis zones for ", new_zone_id
            new_zone_in_street_branch = self.get_in_street_branch(new_zone_id)
            if new_zone_in_street_branch:
                new_branch_zone_id = ZoneUtil.getBranchZone(new_zone_id)
                if new_zone_id % 100 != 0:
                    new_vis_zones.update(self.get_vis_branch_zones(new_zone_id))
                    print "new_vis_zones are ", new_vis_zones
        
        interest.setVisZones(new_vis_zones)
             
        killedZones = []
        old_vis_zones = set()
        if self._interest_manager.has_interest_object_id(interest.getId()):
            previousInterest = self._interest_manager.get_interest_object_by_id(interest.getId())
            
            for zone in previousInterest.getZones():
                if len(self.lookup_interest(previousInterest.getParent(), zone)) > 1:
                    continue
                
                if interest.getParent() != previousInterest.getParent() or not interest.hasZone(zone):
                    killedZones.append(zone)
                
            old_interest_vis_zones = previousInterest.getVisZones()
            #for zone_id in old_interest_vis_zones:
            #    if zone_id in newZones and self.get_in_street_branch(new_zone_id):
            #        print "flush ", zone_id
            #        newZones.remove(zone_id)
            
            interest_vis_zones = interest.getVisZones()
            for zone_id in old_interest_vis_zones.difference(interest_vis_zones):
                print "VIS KILL, ", zone_id
                killedZones.append(zone_id)
                
            for zone_id in interest_vis_zones.difference(old_interest_vis_zones):
                if zone_id not in newZones and not self._interest_manager.has_interest_object_parent_and_zone(interest.getParent(), zone_id):
                    print "VISS ADD, ", zone_id
                    newZones.append(zone_id)
                    
            self.close_zones(killedZones, interest.getParent())
            self._interest_manager.remove_interest_object(self._interest_manager.has_interest_object_id(interest.getId(), True))
        else:
            newZones.extend(list(interest.getVisZones()))
        
        finalZones = []
        for zone in newZones:
            if not self._interest_manager.has_interest_object_parent_and_zone(interest.getParent(), zone, False, True):
                finalZones.append(zone)
        
        self._interest_manager.add_interest_object(interest)
            
        op = InterestOperation(self, 500, interest.getId(), interest.getContext(),
            interest.getParent(), finalZones, self.channel)
        self._pending_interests[interest.getContext()] = interest

        self._deferred_callback = util.DeferredCallback(self.handle_interest_complete_callback, interest.getContext())

        datagram = io.NetworkDatagram()
        datagram.add_header(interest.getParent(), self.channel,
            types.STATESERVER_OBJECT_GET_ZONES_OBJECTS_2)
        datagram.add_uint32(interest.getContext())
        datagram.add_uint16(len(finalZones))
        for zone in finalZones:
            print "zone interest ", zone
            datagram.add_uint32(zone)
            
        print "=============="
        self.network.handle_send_connection_datagram(datagram)
            
    def handle_interest_done(self, interestId, context):
        dg = PyDatagram()
        dg.addUint16(types.CLIENT_DONE_INTEREST_RESP)
        dg.addUint16(interestId)
        dg.addUint32(context)
        self.handle_send_datagram(dg)
        
    def handle_interest_complete_callback(self, complete, contextId):
        print complete, contextId
        if complete:
            if self._pending_interests.has_key(contextId):
                interest = self._pending_interests[contextId]
                self.handle_interest_done(interest.id, contextId)
                del self._pending_interests[contextId]
        else:
            if self._pending_interests.has_key(contextId):
                interest = self._pending_interests[contextId]
                zone = interest.getZones()[-1]
                if zone in self._seen_objects.keys():
                    self.handle_interest_done(interest.id, contextId)
            
    def close_zones(self, kill_zones, parent):
        # send delete for all objects we've seen that were in the zone
        # that we've just left...
        for zone in kill_zones:
            if zone not in PERMA_ZONES and self._seen_objects.has_key(zone):
                seen_objects = self._seen_objects[zone]
                for do_id in seen_objects:
                    # we do not want to delete our owned objects...
                    if do_id not in self._owned_objects:
                        self.send_client_object_delete_resp(do_id)

                del self._seen_objects[zone]
                
                # Tell the State object to stop watching this zone
                datagram = io.NetworkDatagram()
                datagram.add_header(parent, self.channel,
                    types.STATESERVER_OBJECT_CLEAR_WATCH)
                datagram.add_uint32(zone)
                self.network.handle_send_connection_datagram(datagram)
        
    def lookup_interest(self, parent, zone):
        interests = []
        for interest in self._interest_manager.get_interest_objects():
            if interest.getParent() == parent and interest.hasZone(zone):
                interests.append(interest)
                
        return interests
            
    def build_interest(self, di):
        interestId = di.getUint16()
        contextId = di.getUint32()
        parentId = di.getUint32()
        
        interest = Interest()
        interest.setId(interestId)
        interest.setParent(parentId)
        interest.setContext(contextId)
        
        while di.getRemainingSize() > 0:
            interest.addZone(di.getUint32())
        
        return interest
        
    def handle_object_get_zones_objects_resp_2(self, di):
        contextId = di.get_uint32()
        if self._pending_interests.has_key(contextId):
            num_objects = di.get_uint16()
            if num_objects > 0:
                actual_objects = 0
                for _ in range(num_objects):
                    do_id = di.get_uint64()
                    if not self.is_perma_object(do_id) and not self.is_my_avatar(do_id) and not self.has_seen_object(do_id):
                        self._pending_objects.append(do_id)
                        actual_objects += 1
                
                if actual_objects == 0:
                    self._deferred_callback.callback(True)
                    return
                
                if self._deferred_callback:
                    self._deferred_callback.callback(False)      
            else:
                if self._deferred_callback:
                    self._deferred_callback.callback(True)   
        else:
            self.notify.info("Unknown context id recieved %d" %contextId)
            
    def is_perma_object(self, doId):
        for perma_zone in PERMA_ZONES:
            if self._seen_objects.has_key(perma_zone):
                if doId in self._seen_objects[perma_zone]:
                    return True
        
        return False
        
    def is_my_avatar(self, doId):
        return doId == self.get_avatar_id_from_connection_channel(self.channel)
            
    def handle_login(self, di, loginTT = False):
        try:
            play_token = di.get_string()
            server_version = di.get_string()
            hash_val = di.get_uint32()
            token_type = di.get_int32()
        except:
            self.handle_send_disconnect(types.CLIENT_DISCONNECT_TRUNCATED_DATAGRAM,
                'Received truncated datagram from channel: %d!' % (
                    self._channel))

            return

        if server_version != self.network.server_version and server_version != "sv1.0.47.38":
            self.handle_send_disconnect(types.CLIENT_DISCONNECT_BAD_VERSION,
                'Invalid server version: %s, expected: %s!' % (
                    server_version, self.network.server_version))

            return

        if hash_val != self.network.server_hash_val and 0: # Disabled for testing with EXE
            self.handle_send_disconnect(types.CLIENT_DISCONNECT_BAD_DCHASH,
                'Got an invalid dc hash value: %d expected: %d!' % (
                    hash_val, self.network.server_hash_val))

            return

        if token_type != types.CLIENT_LOGIN_2_BLUE and token_type != 4:
            self.handle_send_disconnect(types.CLIENT_DISCONNECT_INVALID_PLAY_TOKEN_TYPE,
                'Invalid play token type: %d!' % (
                    token_type))

            return

        callback = lambda: self.__handle_login_resp(play_token, loginTT)
        self.network.account_manager.handle_operation(LoadAccountFSM, self, callback, play_token)

    def __handle_login_resp(self, play_token, loginTT = False):
        datagram = io.NetworkDatagram()
        datagram.add_uint16(types.CLIENT_LOGIN_2_RESP if not loginTT else 126)
        datagram.add_uint8(0)
        datagram.add_string('All Ok')
        if loginTT:
            datagram.add_uint32(0) # account number
            datagram.add_string("") # account name
            datagram.add_uint8(1) # account name approved
            datagram.add_string("YES") # open chat enabled
            datagram.add_string("YES") # create friends with chat
            datagram.add_string("") # chat code creation rule ?
            datagram.add_uint32(int(time.time())) # sec
            datagram.add_uint32(int(time.clock())) # usec
            datagram.add_string("FULL") # access
            datagram.add_string("YES") # whitelist enabled
            datagram.add_string("") # last logged in
            datagram.add_int32(100000) # account days
            datagram.add_string("WITH_PARENT_ACCOUNT")
            datagram.add_string("") # username
        else:
            datagram.add_string(play_token)
            datagram.add_uint8(1)
            datagram.add_uint32(int(time.time()))
            datagram.add_uint32(int(time.clock()))
            datagram.add_uint8(1)
            datagram.add_int32(1000 * 60 * 60)
        self.handle_send_datagram(datagram)

    def handle_get_shard_list(self):
        datagram = io.NetworkDatagram()
        datagram.add_header(types.STATESERVER_CHANNEL, self.channel,
            types.STATESERVER_GET_SHARD_ALL)

        self.network.handle_send_connection_datagram(datagram)

    def handle_get_shard_list_resp(self, di):
        return
        datagram = io.NetworkDatagram()
        datagram.add_uint16(types.CLIENT_GET_SHARD_LIST_RESP)
        datagram.append_data(di.get_remaining_bytes())
        self.handle_send_datagram(datagram)

    def handle_get_avatars(self):
        account_id = self.get_account_id_from_channel_code(self.channel)
        self.network.account_manager.handle_operation(RetrieveAvatarsFSM, self,
            self.__handle_retrieve_avatars_resp, account_id)

    def __handle_retrieve_avatars_resp(self, avatar_data):
        datagram = io.NetworkDatagram()
        datagram.add_uint16(types.CLIENT_GET_AVATARS_RESP)
        datagram.add_uint8(0)
        datagram.add_uint16(len(avatar_data))

        for avatar in avatar_data:
            datagram.add_uint32(avatar.do_id)
            datagram.add_string(avatar.name_list[0])
            datagram.add_string(avatar.name_list[1])
            datagram.add_string(avatar.name_list[2])
            datagram.add_string(avatar.name_list[3])
            datagram.add_string(avatar.dna)
            datagram.add_uint8(avatar.position)
            datagram.add_uint8(avatar.name_index)

        self.handle_send_datagram(datagram)

    def handle_create_avatar(self, di):
        try:
            echo_context = di.get_uint16()
            dna_string = di.get_string()
            index = di.get_uint8()
        except:
            self.handle_send_disconnect(types.CLIENT_DISCONNECT_TRUNCATED_DATAGRAM,
                'Received truncated datagram from channel: %d!' % (
                    self._channel))

            return

        account_id = self.get_account_id_from_channel_code(self.channel)
        self.network.account_manager.handle_operation(CreateAvatarFSM, self,
            self.__handle_create_avatar_resp, echo_context, account_id, dna_string, index)

    def __handle_create_avatar_resp(self, echo_context, avatar_id):
        datagram = io.NetworkDatagram()
        datagram.add_uint16(types.CLIENT_CREATE_AVATAR_RESP)
        datagram.add_uint16(echo_context)
        datagram.add_uint8(0)
        datagram.add_uint32(avatar_id)
        self.handle_send_datagram(datagram)

    def handle_set_avatar(self, di):
        try:
            avatar_id = di.get_uint32()
        except:
            self.handle_send_disconnect(types.CLIENT_DISCONNECT_TRUNCATED_DATAGRAM,
                'Received truncated datagram from channel: %d!' % (
                    self._channel))

            return

        account_id = self.get_account_id_from_channel_code(self.channel)
        self.network.account_manager.handle_operation(LoadAvatarFSM, self,
            self.__handle_set_avatar_resp, account_id, avatar_id)

    def __handle_set_avatar_resp(self, avatar_id):
        pass

    def handle_friend_online(self, di):
        friend_id = di.get_uint32()

        datagram = io.NetworkDatagram()
        datagram.add_uint16(types.CLIENT_FRIEND_ONLINE)
        datagram.add_uint32(friend_id)
        self.handle_send_datagram(datagram)

    def handle_friend_offline(self, di):
        friend_id = di.get_uint32()

        datagram = io.NetworkDatagram()
        datagram.add_uint16(types.CLIENT_FRIEND_OFFLINE)
        datagram.add_uint32(friend_id)
        self.handle_send_datagram(datagram)

    def handle_get_avatar_details(self, di):
        try:
            avatar_id = di.get_uint32()
        except:
            self.handle_send_disconnect(types.CLIENT_DISCONNECT_TRUNCATED_DATAGRAM,
                'Received truncated datagram from channel: %d!' % (
                    self._channel))

            return

        self.network.account_manager.handle_operation(GetAvatarDetailsFSM, self,
            self.handle_object_enter_owner, avatar_id)

    def handle_set_wishname(self, di):
        try:
            avatar_id = di.get_uint32()
            wish_name = di.get_string()
        except:
            self.handle_send_disconnect(types.CLIENT_DISCONNECT_TRUNCATED_DATAGRAM,
                'Received truncated datagram from channel: %d!' % (
                    self._channel))

            return

        self.network.account_manager.handle_operation(SetNameFSM, self,
            self.__handle_set_wishname_resp, avatar_id, wish_name)

    def __handle_set_wishname_resp(self, avatar_id, wish_name):
        datagram = io.NetworkDatagram()
        datagram.add_uint16(types.CLIENT_SET_WISHNAME_RESP)
        datagram.add_uint32(avatar_id)
        datagram.add_uint16(0)
        datagram.add_string('')
        datagram.add_string(wish_name)
        datagram.add_string('')
        self.handle_send_datagram(datagram)

    def handle_set_name_pattern(self, di):
        try:
            name_indices = []
            name_flags = []
            avatar_id = di.get_uint32()
            name_indices.append(di.get_uint16())
            name_flags.append(di.get_uint16())
            name_indices.append(di.get_uint16())
            name_flags.append(di.get_uint16())
            name_indices.append(di.get_uint16())
            name_flags.append(di.get_uint16())
            name_indices.append(di.get_uint16())
            name_flags.append(di.get_uint16())
        except:
            self.handle_send_disconnect(types.CLIENT_DISCONNECT_TRUNCATED_DATAGRAM,
                'Received truncated datagram from channel: %d!' % self._channel)
            return

        pattern = [
            (name_indices[0], name_flags[0]),
            (name_indices[1], name_flags[1]),
            (name_indices[2], name_flags[2]),
            (name_indices[3], name_flags[3])]

        self.network.account_manager.handle_operation(SetNamePatternFSM, self,
            self.__handle_set_name_pattern_resp, avatar_id, pattern)

    def __handle_set_name_pattern_resp(self, avatar_id):
        datagram = io.NetworkDatagram()
        datagram.add_uint16(types.CLIENT_SET_NAME_PATTERN_ANSWER)
        datagram.add_uint32(avatar_id)
        datagram.add_uint8(0)
        self.handle_send_datagram(datagram)

    def handle_get_friends_list(self, di):
        account_id = self.get_account_id_from_channel_code(self.channel)
        avatar_id = self.get_avatar_id_from_connection_channel(self.channel)

        self.network.account_manager.handle_operation(LoadFriendsListFSM, self,
            self.__handle_get_friends_list_callback, account_id, avatar_id)

    def __handle_get_friends_list_callback(self):
        pass

    def handle_delete_avatar(self, di):
        try:
            avatar_id = di.get_uint32()
        except:
            self.handle_send_disconnect(types.CLIENT_DISCONNECT_TRUNCATED_DATAGRAM,
                'Received truncated datagram from channel: %d!' % (
                    self._channel))

            return

        account_id = self.get_account_id_from_channel_code(self.channel)
        self.network.account_manager.handle_operation(DeleteAvatarFSM, self,
            self.__handle_delete_avatar_resp, account_id, avatar_id)

    def __handle_delete_avatar_resp(self, avatar_data):
        datagram = io.NetworkDatagram()
        datagram.add_uint16(types.CLIENT_DELETE_AVATAR_RESP)
        datagram.add_uint8(0)
        datagram.add_uint16(len(avatar_data))

        for avatar in avatar_data:
            datagram.add_uint32(avatar.do_id)
            datagram.add_string(avatar.name_list[0])
            datagram.add_string(avatar.name_list[1])
            datagram.add_string(avatar.name_list[2])
            datagram.add_string(avatar.name_list[3])
            datagram.add_string(avatar.dna)
            datagram.add_uint8(avatar.position)
            datagram.add_uint8(avatar.name_index)

        self.handle_send_datagram(datagram)

    def handle_set_shard(self, di):
        return
        try:
            shard_id = di.get_uint32()
        except:
            self.handle_send_disconnect(types.CLIENT_DISCONNECT_TRUNCATED_DATAGRAM,
                'Received truncated datagram from channel: %d!' % (
                    self._channel))

            return

        avatar_id = self.get_avatar_id_from_connection_channel(self.channel)
        self._deferred_callback = util.DeferredCallback(self.handle_set_shard_callback)

        datagram = io.NetworkDatagram()
        datagram.add_header(avatar_id, self.channel,
            types.STATESERVER_OBJECT_SET_AI)

        datagram.add_uint64(shard_id - 1)
        self.network.handle_send_connection_datagram(datagram)

    def handle_set_shard_callback(self, do_id, old_parent_id, old_zone_id, new_parent_id, new_zone_id):
        datagram = io.NetworkDatagram()
        datagram.add_uint16(types.CLIENT_GET_STATE_RESP)
        self.handle_send_datagram(datagram)

    def handle_set_zone(self, di):
        return
        try:
            zone_id = di.get_uint16()
        except:
            self.handle_send_disconnect(types.CLIENT_DISCONNECT_TRUNCATED_DATAGRAM,
                'Received truncated datagram from channel: %d!' % (
                    self._channel))

            return

        avatar_id = self.get_avatar_id_from_connection_channel(self.channel)
        self._deferred_callback = util.DeferredCallback(self.handle_set_zone_callback)

        datagram = io.NetworkDatagram()
        datagram.add_header(avatar_id, self.channel,
            types.STATESERVER_OBJECT_SET_ZONE)

        datagram.add_uint32(zone_id)
        self.network.handle_send_connection_datagram(datagram)

    def handle_set_zone_callback(self, do_id, old_parent_id, old_zone_id, new_parent_id, new_zone_id):
        return
        self._deferred_callback.destroy()
        self._deferred_callback = None

        # update the client's interest zones
        self._interest_manager.remove_interest_zone(old_zone_id)
        self._interest_manager.add_interest_zone(new_zone_id)

        # send delete for all objects we've seen that were in the zone
        # that we've just left...
        if old_zone_id in self._seen_objects:
            if old_zone_id != OTP_ZONE_ID_OLD_QUIET_ZONE and old_zone_id != new_zone_id:
                seen_objects = self._seen_objects[old_zone_id]
                for do_id in seen_objects:
                    # we do not want to delete our owned objects...
                    if do_id not in self._owned_objects:
                        self.send_client_object_delete_resp(do_id)

                del self._seen_objects[old_zone_id]

        # request all of the objects in the zones we have interest in
        avatar_id = self.get_avatar_id_from_connection_channel(self.channel)
        self._deferred_callback = util.DeferredCallback(self.handle_set_zone_complete_callback,
            old_parent_id, old_zone_id, new_parent_id, new_zone_id)

        datagram = io.NetworkDatagram()
        datagram.add_header(avatar_id, self.channel,
            types.STATESERVER_OBJECT_GET_ZONES_OBJECTS)

        # pack the interest zones
        interest_zones = list(self._interest_manager.interest_zones)
        datagram.add_uint16(len(interest_zones))
        for interest_zone in interest_zones:
            datagram.add_uint32(interest_zone)

        self.network.handle_send_connection_datagram(datagram)

    def handle_object_location_ack(self, di):
        do_id = di.get_uint32()

        old_parent_id = di.get_uint32()
        old_zone_id = di.get_uint32()

        new_parent_id = di.get_uint32()
        new_zone_id = di.get_uint32()
        
        context = di.get_uint32()
        
        if context != 0:
            if self._context_to_callback.has_key(context):
                callback = self._context_to_callback[context]
                del self._context_to_callback[context]
        else:
            if self._deferred_callback:
                try:
                    self._deferred_callback.callback(do_id, old_parent_id, old_zone_id, new_parent_id, new_zone_id)
                except:
                    pass

    def handle_object_get_zones_objects_resp(self, di):
        do_id = di.get_uint64()
        num_objects = di.get_uint16()
        for _ in range(num_objects):
            self._pending_objects.append(di.get_uint64())

        if self._deferred_callback:
            self._deferred_callback.callback(False)

    def send_client_done_set_zone_resp(self, zone_id):
        datagram = io.NetworkDatagram()
        datagram.add_uint16(types.CLIENT_DONE_SET_ZONE_RESP)
        datagram.add_uint16(zone_id)
        self.handle_send_datagram(datagram)

    def send_client_get_state_resp(self, zone_id):
        datagram = io.NetworkDatagram()
        datagram.add_uint16(types.CLIENT_GET_STATE_RESP)
        datagram.pad_bytes(12)
        datagram.add_uint16(zone_id)
        self.handle_send_datagram(datagram)

    def handle_send_quiet_zone_resp(self, old_zone_id, new_zone_id):
        if not old_zone_id:
            self.send_client_done_set_zone_resp(new_zone_id)
        else:
            self.send_client_get_state_resp(new_zone_id)

        if old_zone_id and new_zone_id != OTP_ZONE_ID_OLD_QUIET_ZONE:
            self.send_client_done_set_zone_resp(new_zone_id)

    def handle_send_zone_resp(self, complete, old_zone_id, new_zone_id):
        if not complete:
            if not old_zone_id:
                self.send_client_done_set_zone_resp(new_zone_id)
            else:
                self.send_client_get_state_resp(new_zone_id)

        if old_zone_id and new_zone_id != OTP_ZONE_ID_OLD_QUIET_ZONE and complete:
            self.send_client_done_set_zone_resp(new_zone_id)

    def handle_set_zone_complete_callback(self, complete, old_parent_id, old_zone_id, new_parent_id, new_zone_id):
        if new_zone_id == OTP_ZONE_ID_OLD_QUIET_ZONE:
            if not complete:
                return

            self.handle_send_quiet_zone_resp(old_zone_id, new_zone_id)
        else:
            self.handle_send_zone_resp(complete, old_zone_id, new_zone_id)

    def handle_object_enter_owner(self, has_other, di):
        do_id = di.get_uint64()
        parent_id = di.get_uint64()
        zone_id = di.get_uint32()
        dc_id = di.get_uint16()

        datagram = io.NetworkDatagram()
        datagram.add_uint16(types.CLIENT_GET_AVATAR_DETAILS_RESP)
        datagram.add_uint32(do_id)
        datagram.add_uint8(0)
        datagram.append_data(di.get_remaining_bytes())
        self.handle_send_datagram(datagram)

        self._owned_objects.append(do_id)

    def handle_object_enter_location(self, has_other, di):
        do_id = di.get_uint64()
        parent_id = di.get_uint64()
        zone_id = di.get_uint32()
        dc_id = di.get_uint16()

        # if the object is in the list of owned objects, we do not want to
        # generate this object, as it was already generated elsewhere...
        if do_id in self._owned_objects:
            return
            
        # check to see if we already generated this object
        # TODO: redo interest handles to avoid this
        if self._seen_objects.has_key(zone_id) and do_id in self._seen_objects[zone_id]:
            return

        # check to see if we have interest in this object's zone, and if we
        # do then we can safely send generate for the object...
        if self._interest_manager.has_interest_object_zone(zone_id):
            datagram = io.NetworkDatagram()
            if not has_other:
                datagram.add_uint16(types.CLIENT_CREATE_OBJECT_REQUIRED)
            else:
                datagram.add_uint16(types.CLIENT_CREATE_OBJECT_REQUIRED_OTHER)

            #2003:
            #datagram.add_uint16(dc_id)
            #datagram.add_uint32(do_id)
            
            datagram.add_uint32(parent_id)
            datagram.add_uint32(zone_id)
            datagram.add_uint16(dc_id)
            datagram.add_uint32(do_id)
            
            datagram.append_data(di.get_remaining_bytes())
            self.handle_send_datagram(datagram)

            #seen_objects = self._seen_objects.setdefault(zone_id, [])
            #seen_objects.append(do_id)
            if not self._seen_objects.has_key(zone_id):
                self._seen_objects[zone_id] = []
            if do_id not in self._seen_objects[zone_id]:
                self._seen_objects[zone_id].append(do_id)

        # even if we are not in the zone of the object, if it's id was being expected
        # by a pending interest we still have to tell it since some objects are moving throughout branches
        # check to see if we have a pending interest handle that is looking
        # to see when this object generate has arrived.
        if do_id in self._pending_objects:
            self._pending_objects.remove(do_id)

            # finally check to see if we have no more pending
            # objects to look for, if so then finish the interest event...
            if len(self._pending_objects) == 0:
                if self._deferred_callback:
                    self._deferred_callback.callback(True)
                    self._deferred_callback.destroy()
                    self._deferred_callback = None

    def send_client_object_delete_resp(self, do_id):
        # if the object is in the list of owned objects, we do not want to
        # delete this object, as it was already generated elsewhere...
        if do_id in self._owned_objects:
            return

        # only delete the object if we've previously seen the objects
        # generate request sent by the StateServer...
        if not self.has_seen_object(do_id, True):
            return

        datagram = io.NetworkDatagram()
        datagram.add_uint16(types.CLIENT_OBJECT_DELETE_RESP)
        datagram.add_uint32(do_id)
        self.handle_send_datagram(datagram)

    def handle_object_delete_ram(self, di):
        doId = di.get_uint32()   
        self.send_client_object_delete_resp(doId)
        for zoneId in self._seen_objects.keys():
            for objId in self._seen_objects[zoneId]:
                if objId == doId:
                    self._seen_objects[zoneId].remove(doId)

    def handle_object_update_field(self, di):
        try:
            do_id = di.get_uint32()
            field_id = di.get_uint16()
        except:
            self.handle_send_disconnect(types.CLIENT_DISCONNECT_TRUNCATED_DATAGRAM,
                'Received truncated datagram from channel: %d!' % (
                    self._channel))

            return

        datagram = io.NetworkDatagram()
        datagram.add_header(do_id, self.channel,
            types.STATESERVER_OBJECT_UPDATE_FIELD)

        datagram.add_uint32(do_id)
        datagram.add_uint16(field_id)

        datagram.append_data(di.get_remaining_bytes())
        self.network.handle_send_connection_datagram(datagram)

    def handle_object_update_field_resp(self, sender, di):
        do_id = di.get_uint32()
        field_id = di.get_uint16()

        # check to see if we either have seen this object's generate already,
        # or that the object is one of our owned objects...
        can_send_update = self.has_seen_object(do_id) or do_id in self._pending_objects or do_id in self._owned_objects
        if not can_send_update:
            return

        datagram = io.NetworkDatagram()
        datagram.add_uint16(types.CLIENT_OBJECT_UPDATE_FIELD_RESP)
        datagram.add_uint32(do_id)
        datagram.add_uint16(field_id)
        datagram.append_data(di.get_remaining_bytes())
        self.handle_send_datagram(datagram)

    def shutdown(self):
        if self.network.account_manager.has_fsm(self.channel):
            self.network.account_manager.stop_operation(self)

        if self.allocated_channel:
            self.network.channel_allocator.free(self.allocated_channel)

        io.NetworkHandler.shutdown(self)

class ClientAgent(io.NetworkListener, io.NetworkConnector):
    notify = notify.new_category('ClientAgent')

    def __init__(self, dc_loader, address, port, connect_address, connect_port, channel):
        io.NetworkListener.__init__(self, address, port, Client)
        io.NetworkConnector.__init__(self, dc_loader, connect_address, connect_port, channel)

        min_channels = config.GetInt('clientagent-min-channels', 1000000000)
        max_channels = config.GetInt('clientagent-max-channels', 1009999999)

        self._channel_allocator = UniqueIdAllocator(min_channels, max_channels - 1)
        self._server_version = config.GetString('clientagent-version', 'no-version')
        self._server_hash_val = int(config.GetString('clientagent-hash-val', '0'))

        self._database_interface = util.DatabaseInterface(self)
        self._account_manager = ClientAccountManager(self)

    @property
    def channel_allocator(self):
        return self._channel_allocator

    @property
    def server_version(self):
        return self._server_version

    @property
    def server_hash_val(self):
        return self._server_hash_val

    @property
    def database_interface(self):
        return self._database_interface

    @property
    def account_manager(self):
        return self._account_manager

    def setup(self):
        io.NetworkListener.setup(self)
        io.NetworkConnector.setup(self)

    def handle_datagram(self, channel, sender, message_type, di):
        handler = self.get_handler_from_channel(channel)
        if not handler:
            self.notify.debug('Cannot handle message type: %d '
                'for unknown channel: %d!' % (message_type, channel))

            return

        handler.handle_internal_datagram(message_type, sender, di)

    def shutdown(self):
        io.NetworkListener.shutdown(self)
        io.NetworkConnector.shutdown(self)
