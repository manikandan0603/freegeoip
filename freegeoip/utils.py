# coding: utf-8
#
# Copyright 2009-2013 Alexandre Fiori
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import cyclone.web
import functools
import socket
import struct

from twisted.internet import defer

from freegeoip.storage import DatabaseSafe


def ip2uint32(address):
    return struct.unpack("!I", socket.inet_aton(address))[0]


def CheckQuota(method):
    @DatabaseSafe
    @defer.inlineCallbacks
    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        key = "ip:%s" % ip2uint32(self.request.remote_ip)

        n = yield self.redis.incr(key)
        if n == 1:
            yield self.redis.expire(key, self.settings.expire)

        elif n > self.settings.max_requests:
            # Over quota, take this.
            raise cyclone.web.HTTPError(403)  # Forbidden

        yield defer.maybeDeferred(method, self, *args, **kwargs)
    return wrapper


class ReservedIPs:
    """List of reserved IPs.
    http://en.wikipedia.org/wiki/Reserved_IP_addresses
    """
    IPs = [
        # network                       netmask
        (ip2uint32("0.0.0.0"),          ip2uint32("255.0.0.0")),
        (ip2uint32("10.0.0.0"),         ip2uint32("255.0.0.0")),
        (ip2uint32("100.64.0.0"),       ip2uint32("255.192.0.0")),
        (ip2uint32("127.0.0.0"),        ip2uint32("255.0.0.0")),
        (ip2uint32("169.254.0.0"),      ip2uint32("255.255.0.0")),
        (ip2uint32("172.16.0.0"),       ip2uint32("255.240.0.0")),
        (ip2uint32("192.0.0.0"),        ip2uint32("255.255.255.248")),
        (ip2uint32("192.0.2.0"),        ip2uint32("255.255.255.0")),
        (ip2uint32("192.88.99.0"),      ip2uint32("255.255.255.0")),
        (ip2uint32("192.168.0.0"),      ip2uint32("255.255.0.0")),
        (ip2uint32("192.18.0.0"),       ip2uint32("255.254.0.0")),
        (ip2uint32("198.51.100.0"),     ip2uint32("255.255.255.0")),
        (ip2uint32("203.0.113.0"),      ip2uint32("255.255.255.0")),
        (ip2uint32("224.0.0.0"),        ip2uint32("240.0.0.0")),
        (ip2uint32("240.0.0.0"),        ip2uint32("240.0.0.0")),
        (ip2uint32("255.255.255.255"),  ip2uint32("255.255.255.255")),
    ]

    @classmethod
    def test(cls, ip):
        for (network, netmask) in cls.IPs:
            if ip & netmask == network:
                return True
        return False
