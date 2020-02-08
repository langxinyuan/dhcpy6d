# DHCPy6d DHCPv6 Daemon
#
# Copyright (C) 2009-2020 Henri Wahl <h.wahl@ifw-dresden.de>
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA 02110-1301, USA

import binascii
import re

from .config import cfg
from .globals import (DUMMY_IAID,
                      DUMMY_MAC,
                      EMPTY_OPTIONS,
                      IGNORED_LOG_OPTIONS,
                      timer)
from .helpers import (colonify_ip6,
                      combine_prefix_length,
                      convert_binary_to_dns,
                      split_prefix)
from .options import OPTIONS


class Transaction:
    """
        all data of one transaction, to be collected in Transactions
    """
    def __init__(self, transaction_id, client_llip, interface, message_type, options):
        # Transaction ID
        self.id = transaction_id
        # Link Local IP of client
        self.client_llip = client_llip
        # Interface the request came in
        self.interface = interface
        # MAC address
        self.mac = DUMMY_MAC
        # last message for following the protocol
        self.last_message_received_type = message_type
        # dictionary for options
        self.options_raw = options
        # default dummy OptionsRequest
        self.options_request = list()
        # timestamp to manage/clean transactions
        self.timestamp = timer
        # dummy hostname
        self.fqdn = ''
        self.hostname = ''
        # DNS Options for option 39
        self.dns_n = 0
        self.dns_o = 0
        self.dns_s = 0
        # dummy IAID
        self.iaid = DUMMY_IAID
        # dummy IAT1
        self.iat1 = cfg.T1
        # dummy IAT2
        self.iat2 = cfg.T2
        # IA option - NA, TA or PD -> DHCPv6 option 3, 4 or 25
        # to be used in option_requests in Handler.build_response()
        self.ia_options = []
        # Addresses given by client, for example for RENEW or RELEASE requests
        self.addresses = []
        # same with prefixes
        self.prefixes = []
        # might be used against clients that are running wild
        # initial 1 as being increased after handling
        self.counter = 1
        # temporary storage for client configuration from DB config
        # - only used if config comes from DB
        self.client_config_db = None
        # client config from config store
        self.client = None
        # Vendor Class Option
        self.vendor_class_en = None
        self.vendor_class_data = ''
        # Rapid Commit flag
        self.rapid_commit = False
        # answer type - take from class definition, one of 'normal', 'noaddress', 'noprefix' or 'none'
        # defaults to 'normal' as this is the main purpose of dhcpy6d
        self.answer = 'normal'
        # default DUID value
        self.duid = ''
        # Elapsed Time - option 8, at least sent by WIDE dhcp6c when requesting delegated prefix
        self.elapsed_time = 0
        # Client architecture type (RFC 5970)
        self.client_architecture = ''
        # Known client architecture type (RFC 4578) (e.g. EFI x86 - 64)
        self.known_client_architecture = ''
        # UserClass (https://tools.ietf.org/html/rfc3315#section-22.15)
        self.user_class = ''

        # if the options have some treatment for transactions just apply it
        for option in options:
            if option in OPTIONS:
                OPTIONS[option].extend_transaction(transaction=self, option=options[option])

    def get_options_string(self):
        """
            get all options in one string for debugging
        """
        options_string = ''
        # put own attributes into a string
        #options = sorted(list(self.__dict__.keys()))
        options = sorted(self.__dict__.keys())
        # options.sort()
        for o in options:
            # ignore some attributes
            if o not in IGNORED_LOG_OPTIONS and \
               not self.__dict__[o] in EMPTY_OPTIONS:
                if o == 'addresses':
                    if (3 or 4) in self.ia_options:
                        option = o + ':'
                        for a in self.__dict__[o]:
                            option += ' ' + colonify_ip6(a)
                        options_string = options_string + ' | '  + option
                elif o == 'prefixes':
                    if 25 in self.ia_options:
                        option = o + ':'
                        for p in self.__dict__[o]:
                            prefix, length = split_prefix(p)
                            option += combine_prefix_length(colonify_ip6(prefix), length)
                elif o == 'client_llip':
                    option = o + ':' + colonify_ip6(self.__dict__[o])
                    options_string = options_string + ' | '  + option
                elif o == 'mac':
                    if self.__dict__[o] != DUMMY_MAC:
                        option = o + ': ' + str(self.__dict__[o])
                        options_string = options_string + ' | ' + option
                else:
                    option = o + ': ' + str(self.__dict__[o])
                    options_string = options_string + ' | '  + option

        return options_string