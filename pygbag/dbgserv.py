#!/usr/bin/env python3.8
# Hey, Emacs! This is -*-python-*-.
#
# Copyright (C) 2003-2019 Joel Rosdahl
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA 02111-1307
# USA
#
# Joel Rosdahl <joel@rosdahl.net>

import sys
import os

from aiolink import autobind

import logging
import os
import re
import select
import socket
import string
import sys
import tempfile
import time
from datetime import datetime
from logging.handlers import RotatingFileHandler
from optparse import OptionParser

VERSION = "1.4"


def buffer_to_socket(msg):
    return msg.encode()


def socket_to_buffer(buf):
    return buf.decode(errors="ignore")


def create_directory(path):
    if not os.path.isdir(path):
        os.makedirs(path)


class Channel(object):
    def __init__(self, server, name):
        self.server = server
        self.name = name
        self.members = set()
        self._topic = ""
        self._key = None
        if self.server.state_dir:
            self._state_path = "%s/%s" % (
                self.server.state_dir,
                name.replace("_", "__").replace("/", "_"),
            )
            self._read_state()
        else:
            self._state_path = None

    def add_member(self, client):
        self.members.add(client)

    def get_topic(self):
        return self._topic

    def set_topic(self, value):
        self._topic = value
        self._write_state()

    topic = property(get_topic, set_topic)

    def get_key(self):
        return self._key

    def set_key(self, value):
        self._key = value
        self._write_state()

    key = property(get_key, set_key)

    def remove_client(self, client):
        self.members.discard(client)
        if not self.members:
            self.server.remove_channel(self)

    def _read_state(self):
        if not (self._state_path and os.path.exists(self._state_path)):
            return
        data = {}

        with open(self._state_path, "rb") as state_file:
            exec(state_file.read(), {}, data)

        self._topic = data.get("topic", "")
        self._key = data.get("key")

    def _write_state(self):
        if not self._state_path:
            return
        (fd, path) = tempfile.mkstemp(dir=os.path.dirname(self._state_path))
        fp = os.fdopen(fd, "w")
        fp.write("topic = %r\n" % self.topic)
        fp.write("key = %r\n" % self.key)
        fp.close()
        os.rename(path, self._state_path)


class Client(object):
    __linesep_regexp = re.compile(r"\r?\n")
    # The RFC limit for nicknames is 9 characters, but what the heck.
    __valid_nickname_regexp = re.compile(r"^[][\`_^{|}A-Za-z][][\`_^{|}A-Za-z0-9-]{0,50}$")
    __valid_channelname_regexp = re.compile(r"^[&#+!][^\x00\x07\x0a\x0d ,:]{0,50}$")

    def __init__(self, server, socket):
        self.server = server
        self.socket = socket
        self.channels = {}  # irc_lower(Channel name) --> Channel
        self.nickname = None
        self.user = None
        self.realname = None
        if self.server.ipv6:
            (self.host, self.port, _, _) = socket.getpeername()
        else:
            (self.host, self.port) = socket.getpeername()
        if self.server.cloak:
            self.host = self.server.cloak
        self.__timestamp = time.time()
        self.__readbuffer = ""
        self.__writebuffer = ""
        self.__sent_ping = False
        if self.server.password:
            self.__handle_command = self.__pass_handler
        else:
            self.__handle_command = self.__registration_handler

    def get_prefix(self):
        return f"{self.nickname}!{self.user}@{self.host}"

    prefix = property(get_prefix)

    def check_aliveness(self):
        now = time.time()
        if self.__timestamp + 180 < now:
            self.disconnect("ping timeout")
            return
        if not self.__sent_ping and self.__timestamp + 90 < now:
            if self.__handle_command == self.__command_handler:
                # Registered.
                self.message("PING :%s" % self.server.name)
                self.__sent_ping = True
            else:
                # Not registered.
                self.disconnect("ping timeout")

    def write_queue_size(self):
        return len(self.__writebuffer)

    def __parse_read_buffer(self):
        lines = self.__linesep_regexp.split(self.__readbuffer)
        self.__readbuffer = lines[-1]
        lines = lines[:-1]
        for line in lines:
            if not line:
                # Empty line. Ignore.
                continue
            print(line)
            x = line.split(" ", 1)
            command = x[0].upper()
            if len(x) == 1:
                arguments = []
            else:
                if len(x[1]) > 0 and x[1][0] == ":":
                    arguments = [x[1][1:]]
                else:
                    y = x[1].split(" :", 1)
                    arguments = y[0].split()
                    if len(y) == 2:
                        arguments.append(y[1])
            self.__handle_command(command, arguments)

    def __pass_handler(self, command, arguments):
        server = self.server
        if command == "PASS":
            if len(arguments) == 0:
                self.reply_461("PASS")
            else:
                if arguments[0] == server.password:
                    self.__handle_command = self.__registration_handler
                else:
                    self.reply("464 :Password incorrect")
        elif command == "QUIT":
            self.disconnect("Client quit")
            return

    def __registration_handler(self, command, arguments):
        server = self.server
        if command == "NICK":
            if len(arguments) < 1:
                self.reply("431 :No nickname given")
                return
            nick = arguments[0]
            if server.get_client(nick):
                self.reply("433 * %s :Nickname is already in use" % nick)
            elif not self.__valid_nickname_regexp.match(nick):
                self.reply("432 * %s :Erroneous nickname" % nick)
            else:
                self.nickname = nick
                server.client_changed_nickname(self, None)
        elif command == "USER":
            if len(arguments) < 4:
                self.reply_461("USER")
                return
            self.user = arguments[0]
            self.realname = arguments[3]
        elif command == "QUIT":
            self.disconnect("Client quit")
            return
        if self.nickname and self.user:
            self.reply("001 %s :Hi, welcome to IRC" % self.nickname)
            self.reply("002 %s :Your host is %s, running version miniircd-%s" % (self.nickname, server.name, VERSION))
            self.reply("003 %s :This server was created sometime" % self.nickname)
            self.reply("004 %s %s miniircd-%s o o" % (self.nickname, server.name, VERSION))
            self.send_lusers()
            self.send_motd()
            self.__handle_command = self.__command_handler

    def __send_names(self, arguments, for_join=False):
        server = self.server
        valid_channel_re = self.__valid_channelname_regexp
        if len(arguments) > 0:
            channelnames = arguments[0].split(",")
        else:
            channelnames = sorted(self.channels.keys())
        if len(arguments) > 1:
            keys = arguments[1].split(",")
        else:
            keys = []
        keys.extend((len(channelnames) - len(keys)) * [None])
        for i, channelname in enumerate(channelnames):
            if for_join and irc_lower(channelname) in self.channels:
                continue
            if not valid_channel_re.match(channelname):
                self.reply_403(channelname)
                continue
            channel = server.get_channel(channelname)
            if channel.key is not None and channel.key != keys[i]:
                self.reply("475 %s %s :Cannot join channel (+k) - bad key" % (self.nickname, channelname))
                continue

            if for_join:
                channel.add_member(self)
                self.channels[irc_lower(channelname)] = channel
                self.message_channel(channel, "JOIN", channelname, True)
                self.channel_log(channel, "joined", meta=True)
                if channel.topic:
                    self.reply("332 %s %s :%s" % (self.nickname, channel.name, channel.topic))
                else:
                    self.reply("331 %s %s :No topic is set" % (self.nickname, channel.name))
            names_prefix = "353 %s = %s :" % (self.nickname, channelname)
            names = ""
            # Max length: reply prefix ":server_name(space)" plus CRLF in
            # the end.
            names_max_len = 512 - (len(server.name) + 2 + 2)
            for name in sorted(x.nickname for x in channel.members):
                if not names:
                    names = names_prefix + name
                # Using >= to include the space between "names" and "name".
                elif len(names) + len(name) >= names_max_len:
                    self.reply(names)
                    names = names_prefix + name
                else:
                    names += " " + name
            if names:
                self.reply(names)
            self.reply("366 %s %s :End of NAMES list" % (self.nickname, channelname))

    def __command_handler(self, command, arguments):
        def away_handler():
            pass

        def ison_handler():
            if len(arguments) < 1:
                self.reply_461("ISON")
                return
            nicks = arguments
            online = [n for n in nicks if server.get_client(n)]
            self.reply("303 %s :%s" % (self.nickname, " ".join(online)))

        def join_handler():
            if len(arguments) < 1:
                self.reply_461("JOIN")
                return
            if arguments[0] == "0":
                for channelname, channel in self.channels.items():
                    self.message_channel(channel, "PART", channelname, True)
                    self.channel_log(channel, "left", meta=True)
                    server.remove_member_from_channel(self, channelname)
                self.channels = {}
                return
            self.__send_names(arguments, for_join=True)

        def list_handler():
            if len(arguments) < 1:
                channels = server.channels.values()
            else:
                channels = []
                for channelname in arguments[0].split(","):
                    if server.has_channel(channelname):
                        channels.append(server.get_channel(channelname))

            sorted_channels = sorted(channels, key=lambda x: x.name)
            for channel in sorted_channels:
                self.reply("322 %s %s %d :%s" % (self.nickname, channel.name, len(channel.members), channel.topic))
            self.reply("323 %s :End of LIST" % self.nickname)

        def lusers_handler():
            self.send_lusers()

        def mode_handler():
            if len(arguments) < 1:
                self.reply_461("MODE")
                return
            targetname = arguments[0]
            if server.has_channel(targetname):
                channel = server.get_channel(targetname)
                if len(arguments) < 2:
                    if channel.key:
                        modes = "+k"
                        if irc_lower(channel.name) in self.channels:
                            modes += " %s" % channel.key
                    else:
                        modes = "+"
                    self.reply("324 %s %s %s" % (self.nickname, targetname, modes))
                    return
                flag = arguments[1]
                if flag == "+k":
                    if len(arguments) < 3:
                        self.reply_461("MODE")
                        return
                    key = arguments[2]
                    if irc_lower(channel.name) in self.channels:
                        channel.key = key
                        self.message_channel(channel, "MODE", "%s +k %s" % (channel.name, key), True)
                        self.channel_log(channel, "set channel key to %s" % key, meta=True)
                    else:
                        self.reply("442 %s :You're not on that channel" % targetname)
                elif flag == "-k":
                    if irc_lower(channel.name) in self.channels:
                        channel.key = None
                        self.message_channel(channel, "MODE", "%s -k" % channel.name, True)
                        self.channel_log(channel, "removed channel key", meta=True)
                    else:
                        self.reply("442 %s :You're not on that channel" % targetname)
                else:
                    self.reply("472 %s %s :Unknown MODE flag" % (self.nickname, flag))
            elif targetname == self.nickname:
                if len(arguments) == 1:
                    self.reply("221 %s +" % self.nickname)
                else:
                    self.reply("501 %s :Unknown MODE flag" % self.nickname)
            else:
                self.reply_403(targetname)

        def motd_handler():
            self.send_motd()

        def names_handler():
            self.__send_names(arguments)

        def nick_handler():
            if len(arguments) < 1:
                self.reply("431 :No nickname given")
                return
            newnick = arguments[0]
            client = server.get_client(newnick)
            if newnick == self.nickname:
                pass
            elif client and client is not self:
                self.reply("433 %s %s :Nickname is already in use" % (self.nickname, newnick))
            elif not self.__valid_nickname_regexp.match(newnick):
                self.reply("432 %s %s :Erroneous Nickname" % (self.nickname, newnick))
            else:
                for x in self.channels.values():
                    self.channel_log(x, "changed nickname to %s" % newnick, meta=True)
                oldnickname = self.nickname
                self.nickname = newnick
                server.client_changed_nickname(self, oldnickname)
                self.message_related(
                    ":%s!%s@%s NICK %s" % (oldnickname, self.user, self.host, self.nickname),
                    True,
                )

        def notice_and_privmsg_handler():
            if len(arguments) == 0:
                self.reply("411 %s :No recipient given (%s)" % (self.nickname, command))
                return
            if len(arguments) == 1:
                self.reply("412 %s :No text to send" % self.nickname)
                return
            targetname = arguments[0]
            message = arguments[1]
            client = server.get_client(targetname)
            if client:
                client.message(":%s %s %s :%s" % (self.prefix, command, targetname, message))
            elif server.has_channel(targetname):
                channel = server.get_channel(targetname)
                self.message_channel(channel, command, "%s :%s" % (channel.name, message))
                self.channel_log(channel, message)
            else:
                self.reply("401 %s %s :No such nick/channel" % (self.nickname, targetname))

        def part_handler():
            if len(arguments) < 1:
                self.reply_461("PART")
                return
            if len(arguments) > 1:
                partmsg = arguments[1]
            else:
                partmsg = self.nickname
            for channelname in arguments[0].split(","):
                if not valid_channel_re.match(channelname):
                    self.reply_403(channelname)
                elif not irc_lower(channelname) in self.channels:
                    self.reply("442 %s %s :You're not on that channel" % (self.nickname, channelname))
                else:
                    channel = self.channels[irc_lower(channelname)]
                    self.message_channel(channel, "PART", "%s :%s" % (channelname, partmsg), True)
                    self.channel_log(channel, "left (%s)" % partmsg, meta=True)
                    del self.channels[irc_lower(channelname)]
                    server.remove_member_from_channel(self, channelname)

        def ping_handler():
            if len(arguments) < 1:
                self.reply("409 %s :No origin specified" % self.nickname)
                return
            self.reply("PONG %s :%s" % (server.name, arguments[0]))

        def pong_handler():
            pass

        def quit_handler():
            if len(arguments) < 1:
                quitmsg = self.nickname
            else:
                quitmsg = arguments[0]
            self.disconnect(quitmsg)

        def topic_handler():
            if len(arguments) < 1:
                self.reply_461("TOPIC")
                return
            channelname = arguments[0]
            channel = self.channels.get(irc_lower(channelname))
            if channel:
                if len(arguments) > 1:
                    newtopic = arguments[1]
                    channel.topic = newtopic
                    self.message_channel(channel, "TOPIC", "%s :%s" % (channelname, newtopic), True)
                    self.channel_log(channel, "set topic to %r" % newtopic, meta=True)
                else:
                    if channel.topic:
                        self.reply("332 %s %s :%s" % (self.nickname, channel.name, channel.topic))
                    else:
                        self.reply("331 %s %s :No topic is set" % (self.nickname, channel.name))
            else:
                self.reply("442 %s :You're not on that channel" % channelname)

        def wallops_handler():
            if len(arguments) < 1:
                self.reply_461("WALLOPS")
                return
            message = arguments[0]
            for client in server.clients.values():
                client.message(":%s NOTICE %s :Global notice: %s" % (self.prefix, client.nickname, message))

        def who_handler():
            if len(arguments) < 1:
                return
            targetname = arguments[0]
            if server.has_channel(targetname):
                channel = server.get_channel(targetname)
                for member in channel.members:
                    self.reply(
                        "352 %s %s %s %s %s %s H :0 %s"
                        % (
                            self.nickname,
                            targetname,
                            member.user,
                            member.host,
                            server.name,
                            member.nickname,
                            member.realname,
                        )
                    )
                self.reply("315 %s %s :End of WHO list" % (self.nickname, targetname))

        def whois_handler():
            if len(arguments) < 1:
                return
            username = arguments[0]
            user = server.get_client(username)
            if user:
                self.reply(
                    "311 %s %s %s %s * :%s"
                    % (
                        self.nickname,
                        user.nickname,
                        user.user,
                        user.host,
                        user.realname,
                    )
                )
                self.reply("312 %s %s %s :%s" % (self.nickname, user.nickname, server.name, server.name))
                self.reply(
                    "319 %s %s :%s"
                    % (
                        self.nickname,
                        user.nickname,
                        "".join(x + " " for x in user.channels),
                    )
                )
                self.reply("318 %s %s :End of WHOIS list" % (self.nickname, user.nickname))
            else:
                self.reply("401 %s %s :No such nick" % (self.nickname, username))

        handler_table = {
            "AWAY": away_handler,
            "ISON": ison_handler,
            "JOIN": join_handler,
            "LIST": list_handler,
            "LUSERS": lusers_handler,
            "MODE": mode_handler,
            "MOTD": motd_handler,
            "NAMES": names_handler,
            "NICK": nick_handler,
            "NOTICE": notice_and_privmsg_handler,
            "PART": part_handler,
            "PING": ping_handler,
            "PONG": pong_handler,
            "PRIVMSG": notice_and_privmsg_handler,
            "QUIT": quit_handler,
            "TOPIC": topic_handler,
            "WALLOPS": wallops_handler,
            "WHO": who_handler,
            "WHOIS": whois_handler,
        }
        server = self.server
        valid_channel_re = self.__valid_channelname_regexp
        try:
            handler_table[command]()
        except KeyError:
            self.reply("421 %s %s :Unknown command" % (self.nickname, command))

    def socket_readable_notification(self):
        try:
            data = self.socket.recv(2**10)
            self.server.print_debug("[%s:%d] -> %r" % (self.host, self.port, data))
            quitmsg = "EOT"
        except socket.error as x:
            data = ""
            quitmsg = x
        if data:
            self.__readbuffer += socket_to_buffer(data)
            self.__parse_read_buffer()
            self.__timestamp = time.time()
            self.__sent_ping = False
        else:
            self.disconnect(quitmsg)

    def socket_writable_notification(self):
        try:
            sent = self.socket.send(buffer_to_socket(self.__writebuffer))
            self.server.print_debug("[%s:%d] <- %r" % (self.host, self.port, self.__writebuffer[:sent]))
            self.__writebuffer = self.__writebuffer[sent:]
        except socket.error as x:
            self.disconnect(x)

    def disconnect(self, quitmsg):
        self.message("ERROR :%s" % quitmsg)
        self.server.print_info("Disconnected connection from %s:%s (%s)." % (self.host, self.port, quitmsg))
        self.socket.close()
        self.server.remove_client(self, quitmsg)

    def message(self, msg):
        self.__writebuffer += msg + "\r\n"

    def reply(self, msg):
        self.message(":%s %s" % (self.server.name, msg))

    def reply_403(self, channel):
        self.reply("403 %s %s :No such channel" % (self.nickname, channel))

    def reply_461(self, command):
        nickname = self.nickname or "*"
        self.reply("461 %s %s :Not enough parameters" % (nickname, command))

    def message_channel(self, channel, command, message, include_self=False):
        line = ":%s %s %s" % (self.prefix, command, message)
        for client in channel.members:
            if client != self or include_self:
                client.message(line)

    def channel_log(self, channel, message, meta=False):
        if not self.server.channel_log_dir:
            return
        if meta:
            format = "[%s] * %s %s\n"
        else:
            format = "[%s] <%s> %s\n"
        timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
        logname = irc_lower(channel.name).replace("_", "__").replace("/", "_")
        fp = open("%s/%s.log" % (self.server.channel_log_dir, logname), "a")
        fp.write(format % (timestamp, self.nickname, message))
        fp.close()

    def message_related(self, msg, include_self=False):
        clients = set()
        if include_self:
            clients.add(self)
        for channel in self.channels.values():
            clients |= channel.members
        if not include_self:
            clients.discard(self)
        for client in clients:
            client.message(msg)

    def send_lusers(self):
        self.reply("251 %s :There are %d users and 0 services on 1 server" % (self.nickname, len(self.server.clients)))

    def send_motd(self):
        server = self.server
        motdlines = server.get_motd_lines()
        if motdlines:
            self.reply("375 %s :- %s Message of the day -" % (self.nickname, server.name))
            for line in motdlines:
                self.reply("372 %s :- %s" % (self.nickname, line.rstrip()))
            self.reply("376 %s :End of /MOTD command" % self.nickname)
        else:
            self.reply("422 %s :MOTD File is missing" % self.nickname)


class Server(object):
    def __init__(self, options):
        self.ports = options.ports
        self.password = options.password
        self.ssl_pem_file = options.ssl_pem_file
        self.motdfile = options.motd
        self.verbose = options.verbose
        self.ipv6 = options.ipv6
        self.debug = options.debug
        self.channel_log_dir = options.channel_log_dir
        self.chroot = options.chroot
        self.setuid = options.setuid
        self.state_dir = options.state_dir
        self.log_file = options.log_file
        self.log_max_bytes = options.log_max_size * 1024 * 1024
        self.log_count = options.log_count
        self.logger = None
        self.cloak = options.cloak

        if options.password_file:
            with open(options.password_file, "r") as fp:
                self.password = fp.read().strip("\n")

        if self.ssl_pem_file:
            self.ssl = __import__("ssl")

        # Find certificate after daemonization if path is relative:
        if self.ssl_pem_file and os.path.exists(self.ssl_pem_file):
            self.ssl_pem_file = os.path.abspath(self.ssl_pem_file)
        # else: might exist in the chroot jail, so just continue

        if options.listen and self.ipv6:
            self.address = socket.getaddrinfo(options.listen, None, proto=socket.IPPROTO_TCP)[0][4][0]
        elif options.listen:
            self.address = socket.gethostbyname(options.listen)
        else:
            self.address = ""
        server_name_limit = 63  # From the RFC.
        self.name = socket.getfqdn(self.address)[:server_name_limit]

        self.channels = {}  # irc_lower(Channel name) --> Channel instance.
        self.clients = {}  # Socket --> Client instance.
        self.nicknames = {}  # irc_lower(Nickname) --> Client instance.
        if self.channel_log_dir:
            create_directory(self.channel_log_dir)
        if self.state_dir:
            create_directory(self.state_dir)

    def make_pid_file(self, filename):
        try:
            fd = os.open(filename, os.O_RDWR | os.O_CREAT | os.O_EXCL, 0o644)
            os.write(fd, "%i\n" % os.getpid())
            os.close(fd)
        except:
            self.print_error("Could not create PID file %r" % filename)
            sys.exit(1)

    def get_client(self, nickname):
        return self.nicknames.get(irc_lower(nickname))

    def has_channel(self, name):
        return irc_lower(name) in self.channels

    def get_channel(self, channelname):
        if irc_lower(channelname) in self.channels:
            channel = self.channels[irc_lower(channelname)]
        else:
            channel = Channel(self, channelname)
            self.channels[irc_lower(channelname)] = channel
        return channel

    def get_motd_lines(self):
        if self.motdfile:
            try:
                return open(self.motdfile).readlines()
            except IOError:
                return ["Could not read MOTD file %r." % self.motdfile]
        else:
            return []

    def print_info(self, msg):
        if self.verbose:
            print(msg)
            sys.stdout.flush()
        if self.logger:
            self.logger.info(msg)

    def print_debug(self, msg):
        if self.debug:
            print(msg)
            sys.stdout.flush()
        if self.logger:
            self.logger.debug(msg)

    def print_error(self, msg):
        sys.stderr.write("%s\n" % msg)
        if self.logger:
            self.logger.error(msg)

    def client_changed_nickname(self, client, oldnickname):
        if oldnickname:
            del self.nicknames[irc_lower(oldnickname)]
        self.nicknames[irc_lower(client.nickname)] = client

    def remove_member_from_channel(self, client, channelname):
        if irc_lower(channelname) in self.channels:
            channel = self.channels[irc_lower(channelname)]
            channel.remove_client(client)

    def remove_client(self, client, quitmsg):
        client.message_related(":%s QUIT :%s" % (client.prefix, quitmsg))
        for x in client.channels.values():
            client.channel_log(x, "quit (%s)" % quitmsg, meta=True)
            x.remove_client(client)
        if client.nickname and irc_lower(client.nickname) in self.nicknames:
            del self.nicknames[irc_lower(client.nickname)]
        del self.clients[client.socket]

    def remove_channel(self, channel):
        del self.channels[irc_lower(channel.name)]

    def start(self):
        serversockets = []
        for port in self.ports:
            s = socket.socket(socket.AF_INET6 if self.ipv6 else socket.AF_INET, socket.SOCK_STREAM)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            try:
                s.bind((self.address, port))
            except socket.error as e:
                self.print_error("Could not bind port %s: %s." % (port, e))
                sys.exit(1)
            s.listen(5)
            serversockets.append(s)
            del s
            self.print_info("Listening on port %d." % port)
        if self.chroot:
            os.chdir(self.chroot)
            os.chroot(self.chroot)
            self.print_info("Changed root directory to %s" % self.chroot)
        if self.setuid:
            os.setgid(self.setuid[1])
            os.setuid(self.setuid[0])
            self.print_info("Setting uid:gid to %s:%s" % (self.setuid[0], self.setuid[1]))

        self.init_logging()
        try:
            self.run(serversockets)
        except:
            if self.logger:
                self.logger.exception("Fatal exception")
            raise

    def init_logging(self):
        if not self.log_file:
            return

        log_level = logging.INFO
        if self.debug:
            log_level = logging.DEBUG
        self.logger = logging.getLogger("miniircd")
        formatter = logging.Formatter(("%(asctime)s - %(name)s[%(process)d] - " "%(levelname)s - %(message)s"))
        fh = RotatingFileHandler(self.log_file, maxBytes=self.log_max_bytes, backupCount=self.log_count)
        fh.setLevel(log_level)
        fh.setFormatter(formatter)
        self.logger.setLevel(log_level)
        self.logger.addHandler(fh)

    def run(self, serversockets):
        last_aliveness_check = time.time()
        while True:
            (iwtd, owtd, ewtd) = select.select(
                serversockets + [x.socket for x in self.clients.values()],
                [x.socket for x in self.clients.values() if x.write_queue_size() > 0],
                [],
                10,
            )
            for x in iwtd:
                if x in self.clients:
                    self.clients[x].socket_readable_notification()
                else:
                    (conn, addr) = x.accept()
                    if self.ssl_pem_file:
                        try:
                            conn = self.ssl.wrap_socket(
                                conn,
                                server_side=True,
                                certfile=self.ssl_pem_file,
                                keyfile=self.ssl_pem_file,
                            )
                        except Exception as e:
                            self.print_error("SSL error for connection from %s:%s: %s" % (addr[0], addr[1], e))
                            continue
                    try:
                        self.clients[conn] = Client(self, conn)
                        self.print_info("Accepted connection from %s:%s." % (addr[0], addr[1]))
                    except socket.error as e:
                        try:
                            conn.close()
                        except:
                            pass
            for x in owtd:
                if x in self.clients:  # client may have been disconnected
                    self.clients[x].socket_writable_notification()
            now = time.time()
            if last_aliveness_check + 10 < now:
                for client in list(self.clients.values()):
                    client.check_aliveness()
                last_aliveness_check = now


_maketrans = str.maketrans if PY3 else string.maketrans
_ircstring_translation = _maketrans(string.ascii_lowercase.upper() + "[]\\^", string.ascii_lowercase + "{}|~")


def irc_lower(s):
    return s.translate(_ircstring_translation)


def main(argv):
    op = OptionParser(version=VERSION, description="miniircd is a small and limited IRC server.")
    op.add_option("--channel-log-dir", metavar="X", help="store channel log in directory X")
    op.add_option("--ipv6", action="store_true", help="use IPv6")
    op.add_option("--debug", action="store_true", help="print debug messages to stdout")
    op.add_option("--listen", metavar="X", help="listen on specific IP address X")
    op.add_option(
        "--log-count",
        metavar="X",
        default=10,
        type="int",
        help="keep X log files; default: %default",
    )
    op.add_option("--log-file", metavar="X", help="store log in file X")
    op.add_option(
        "--log-max-size",
        metavar="X",
        default=10,
        type="int",
        help="set maximum log file size to X MiB; default: %default MiB",
    )
    op.add_option("--motd", metavar="X", help="display file X as message of the day")
    op.add_option("--pid-file", metavar="X", help="write PID to file X")
    op.add_option(
        "-p",
        "--password",
        metavar="X",
        help="require connection password X; default: no password",
    )
    op.add_option(
        "--password-file",
        metavar="X",
        help=("require connection password stored in file X;" " default: no password"),
    )
    op.add_option(
        "--ports",
        metavar="X",
        help="listen to ports X (a list separated by comma or whitespace);" " default: 6667 or 6697 if SSL is enabled",
    )
    op.add_option(
        "-s",
        "--ssl-pem-file",
        metavar="FILE",
        help="enable SSL and use FILE as the .pem certificate+key",
    )
    op.add_option(
        "--state-dir",
        metavar="X",
        help="save persistent channel state (topic, key) in directory X",
    )
    op.add_option(
        "--verbose",
        action="store_true",
        help="be verbose (print some progress messages to stdout)",
    )
    op.add_option("--cloak", metavar="X", help="report X as the host for all clients")
    if os.name == "posix":
        op.add_option(
            "--chroot",
            metavar="X",
            help="change filesystem root to directory X after startup" " (requires root)",
        )
        op.add_option(
            "--setuid",
            metavar="U[:G]",
            help="change process user (and optionally group) after startup" " (requires root)",
        )

    (options, args) = op.parse_args(argv[1:])
    if os.name != "posix":
        options.chroot = False
        options.setuid = False
    if options.debug:
        options.verbose = True
    if options.ports is None:
        if options.ssl_pem_file is None:
            options.ports = "6667"
        else:
            options.ports = "6697"
    if options.chroot and os.getuid() != 0:
        op.error("Must be root to use --chroot")
    if options.setuid:
        from pwd import getpwnam
        from grp import getgrnam

        if os.getuid() != 0:
            op.error("Must be root to use --setuid")
        matches = options.setuid.split(":")
        if len(matches) == 2:
            options.setuid = (getpwnam(matches[0]).pw_uid, getgrnam(matches[1]).gr_gid)
        elif len(matches) == 1:
            options.setuid = (getpwnam(matches[0]).pw_uid, getpwnam(matches[0]).pw_gid)
        else:
            op.error("Specify a user, or user and group separated by a colon," " e.g. --setuid daemon, --setuid nobody:nobody")
    if os.name == "posix" and not options.setuid and (os.getuid() == 0 or os.getgid() == 0):
        op.error(
            "Running this service as root is not recommended. Use the"
            " --setuid option to switch to an unprivileged account after"
            " startup. If you really intend to run as root, use"
            ' "--setuid root".'
        )

    ports = []
    for port in re.split(r"[,\s]+", options.ports):
        try:
            ports.append(int(port))
        except ValueError:
            op.error("bad port: %r" % port)
    options.ports = ports
    server = Server(options)

    if options.pid_file:
        server.make_pid_file(options.pid_file)
    try:
        server.start()
    except KeyboardInterrupt:
        server.print_error("Interrupted.")


if __name__ == "__main__":
    main(sys.argv)
