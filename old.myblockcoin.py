# from try.docopt.org
"""
BankNetCoin

Usage:
  mybanknetcoin.py serve
  mybanknetcoin.py ping
  mybanknetcoin.py balance <name>
  mybanknetcoin.py tx <from> <to> <amount>

Options:
  -h --help     Show this screen.

"""


import uuid, socketserver, socket, sys
from copy import deepcopy
from ecdsa import SigningKey, SECP256k1
from utils import serialize, deserialize, prepare_simple_tx
from identities import user_public_key, user_private_key
from docopt import docopt

def spend_message(tx, index):
    tx_in = tx.tx_ins[index]
    outpoint = tx_in.outpoint
    return serialize(outpoint) + serialize(tx.tx_outs)


class Tx:

    def __init__(self, id, tx_ins, tx_outs):
        self.id = id
        self.tx_ins = tx_ins
        self.tx_outs = tx_outs

    def sign_input(self, index, private_key):
        message = spend_message(self, index)
        signature = private_key.sign(message)
        self.tx_ins[index].signature = signature

    def verify_input(self, index, public_key):
        tx_in = self.tx_ins[index]
        message = spend_message(self, index)
        return public_key.verify(tx_in.signature, message)

class TxIn:

    def __init__(self, tx_id, index, signature=None):
        self.tx_id = tx_id
        self.index = index
        self.signature = signature


    @property
    def outpoint(self):
        return (self.tx_id, self.index)

class TxOut:

    def __init__(self, tx_id, index, amount, public_key):
        self.tx_id = tx_id
        self.index = index
        self.amount = amount
        self.public_key = public_key

    @property
    def outpoint(self):
        return (self.tx_id, self.index)

class Bank:

    def __init__(self, id, private_key):
        self.id = id
        self.private_key = private_key
        self.blocks = []
        self.utxo_set = {}
        self.mempool = []



    def update_utxo(self, tx):
        for tx_out in tx.tx_outs:
            self.utxo[tx_out.outpoint] = tx_out
        for tx_in in tx.tx_ins:
            del self.utxo[tx_in.outpoint]

    def issue(self, amount, public_key):
        id_ = str(uuid.uuid4())
        tx_ins = []
        tx_outs = [TxOut(tx_id=id_, index=0, amount=amount, public_key=public_key)]
        tx = Tx(id=id_, tx_ins=tx_ins, tx_outs=tx_outs)

        self.update_utxo(tx)

        return tx

    def validate_tx(self, tx):
        in_sum = 0
        out_sum = 0
        for index, tx_in in enumerate(tx.tx_ins):
            assert tx_in.outpoint in self.utxo

            tx_out = self.utxo[tx_in.outpoint]
            # Verify signature using public key of TxOut we're spending
            public_key = tx_out.public_key
            tx.verify_input(index, public_key)

            # Sum up the total inputs
            amount = tx_out.amount
            in_sum += amount

        for tx_out in tx.tx_outs:
            out_sum += tx_out.amount

        assert in_sum == out_sum

    def handle_tx(self, tx):
        # Save to self.utxo if it's valid
        self.validate_tx(tx)
        self.update_utxo(tx)

    def fetch_utxo(self, public_key):
        return [utxo for utxo in self.utxo.values() 
                if utxo.public_key == public_key]

    def fetch_balance(self, public_key):
        # Fetch utxo associated with this public key
        unspents = self.fetch_utxo(public_key)
        # Sum the amounts
        return sum([tx_out.amount for tx_out in unspents])

def prepare_message(command, data):
    return {
        "command": command,
        "data": data,
    }


# paste the my_ping_pong server into bottom of the file
host = "0.0.0.0"
port = 10000
address = (host, port)
# instantiate a new single instance of bank for the response handler
bank = None

# this is a sub-class which flips this single parameter to True
class MyTCPServer(socketserver.TCPServer):
    # from https://docs.python.org/3/library/socketserver.html#socketserver.BaseServer.allow_reuse_address
    allow_reuse_address = True


# this is running a socket server in python
class TCPHandler(socketserver.BaseRequestHandler):

    def respond(self, command, data):
        response = prepare_message(command, data)
        serialized_response = serialize(response)
        self.request.sendall(serialized_response)
        self.request.sendall(serialized_response)

    def handle(self):
        message_data = self.request.recv(5000).strip()
        message = deserialize(message_data)
        command = message["command"]

        print(f"Got a  message: {message}")

        if command == "ping":
            self.respond("pong", "")

        if command == "balance":
            public_key = message["data"]
            balance = bank.fetch_balance(public_key)
            self.respond("balance-response", balance)

        if command == "utxo":
            public_key = message["data"]
            utxo = bank.fetch_utxo(public_key)
            self.respond("utxo-response", utxo)

        if command == "tx":
            tx = message["data"]
            try:
                bank.handle_tx(tx)
                self.respond("tx-response", data="accepted")
            except:
                self.respond("tx-response", data="rejected")



# lets make some code that can run this handler above
def serve():
    server = MyTCPServer(address, TCPHandler)
    server.serve_forever()

def send_message(command, data):
    # create a IP (AF_INET), TCP (SOCK_STREAM) type socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect(address)

    #create and serialize the message
    message = prepare_message(command, data)
    serialized_message = serialize(message)
    # send the message
    sock.sendall(serialized_message)

    # get a response and print it out
    message_data = sock.recv(5000)
    message = deserialize(message_data)
    print(f"Recieved {message}")

    return message

# client side stuff here:
def main(args):
    if args["serve"]:
        # HACK! issue alice a balance so that we can play with the
        # system
        alice_public_key = user_public_key("alice")
        bank.issue(1000, alice_public_key)

        serve()

    elif args["ping"]:
        send_message("ping", "")

    elif args["balance"]:
        name = args["<name>"]
        public_key = user_public_key(name)
        send_message("balance", public_key)

    elif args["tx"]:

        sender_private_key = user_private_key(args["<from>"])
        sender_public_key = sender_private_key.get_verifying_key()
        recipient_public_key = user_public_key(args["<to>"])
        amount = int(args["<amount>"])

        # fetch sender's UTXOs to construct tx INs of new tx
        utxo_response = send_message("utxo", sender_public_key)
        utxo = utxo_response["data"]

        # prepare the transaction
        tx = prepare_simple_tx(utxo,
                               sender_private_key,
                               recipient_public_key,
                               amount)


        # send the tx to the bank
        response = send_message("tx", tx)
        print(response)


    else:
        print("invalid command")


# define a way to call serve when someone runs the file
# this lets python know the user is running from the command line
# and not just importing it some where else.
if __name__ == "__main__":
    # parse the sys.argv values according to our docopt file
    args = docopt(__doc__)
    main(args)






































