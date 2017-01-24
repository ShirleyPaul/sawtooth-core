# Copyright 2017 Intel Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ------------------------------------------------------------------------------
import logging

from sawtooth_cli.exceptions import CliException

from sawtooth_protobuf.batch_pb2 import BatchList
from sawtooth_protobuf.genesis_pb2 import GenesisData
from sawtooth_protobuf.transaction_pb2 import TransactionHeader


LOGGER = logging.getLogger(__name__)


def add_genesis_parser(subparsers, parent_parser):
    """Creates the arg parsers needed for the genesis command.
    """
    parser = subparsers.add_parser('genesis')

    parser.add_argument(
        '-o', '--output',
        type=str,
        default='genesis.batch',
        help='the name of the file to ouput the GenesisData')

    parser.add_argument(
        'input_file',
        nargs='+',
        type=str,
        help='input files of batches to add to the resulting GenesisData')


def do_genesis(args):
    """Given the command args, take an series of input files containing
    GenesisData, combine all the batches into one GenesisData, and output the
    result into a new file.
    """
    genesis_batches = []
    for input_file in args.input_file:
        LOGGER.info('Processing %s...', input_file)
        input_data = BatchList()
        with open(input_file, 'rb') as in_file:
            input_data.ParseFromString(in_file.read())
        genesis_batches += input_data.batches

    _validate_depedencies(genesis_batches)

    LOGGER.info('Generating %s', args.output)
    output_data = GenesisData(batches=genesis_batches)
    with open(args.output, 'wb') as out_file:
        out_file.write(output_data.SerializeToString())


def _validate_depedencies(batches):
    """Validates the transaction dependencies for the transactions contained
    within the sequence of batches. Given that all the batches are expected to
    to be executed for the genesis blocks, it is assumed that any dependent
    transaction will proceed the depending transaction.
    """
    transaction_ids = set()
    for batch in batches:
        for txn in batch.transactions:
            txn_header = TransactionHeader()
            txn_header.ParseFromString(txn.header)

            if len(txn_header.dependencies) > 0:
                unsatisfied_deps = [id for id in txn_header.dependencies
                                    if id not in transaction_ids]
                if len(unsatisfied_deps) != 0:
                    raise CliException(
                        'Unsatisfied dependency in given transactions:'
                        ' {}'.format(unsatisfied_deps))

            transaction_ids.add(txn.header_signature)
