import hashlib
import json
from textwrap import dedent
from time import time
from uuid import uuid4
from flask import Flask, jsonify, request
from urllib.parse import urlparse
import requests

class Blockchain:
    def __init__(self):
        self.chain = []
        self.current_transactions = []

        self.nodes = set()

        # make the genesis block
        self.new_block(previous_hash = 1, proof = 100)

    # make new block & add it to the chain
    def new_block(self, proof, previous_hash = None):
        block = {
            'index' : len(self.chain) + 1,
            'timestamp' : time(),
            'transactions' : self.current_transactions,
            'proof' : proof,
            'previous_hash' : previous_hash or self.hash(self.chain[-1]),
            }

        # reset current transactions
        self.current_transactions = []

        self.chain.append(block)
        return block

    # make new transactin & add it to the list that will be added to next block
    def new_transaction(self, sender, recipient, amount):
        self.current_transactions.append({
            'sender' : sender,
            'recipient' :recipient,
            'amount' : amount,
            })
        return self.last_block['index'] + 1

    # get last block of the chain
    @property
    def last_block(self):
        return self.chain[-1]

    # make hash number from a block
    @staticmethod
    def hash(block):
        block_string = json.dumps(block, sort_keys = True).encode()
        return hashlib.sha256(block_string).hexdigest()

    # algorithm of PoW
    def proof_of_work(self, last_proof):
        proof = 0
        while self.valid_proof(last_proof, proof) is False:
            proof += 1
        return proof

    # valid if not proof is true
    @staticmethod
    def valid_proof(last_proof, proof):
        guess = '{}{}'.format(last_proof, proof).encode()
        guess_hash = hashlib.sha256(guess).hexdigest()

        return guess_hash[:4] == "0000"

    def register_node(self, address):
        parsed_url = urlparse(address)
        self.nodes.add(parsed_url.netloc)

    # check whether chain is valid
    def valid_chain(self, chain):
        last_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]
            print('{}'.format(last_block))
            print('{}'.format(block))
            print('\n-------------\n')

            # check whether hash is correct
            if block['previous_hash'] != self.hash(last_block):
                return False

            # check whether PoW is correct
            if not self.valid_proof(last_block['proof'], block['proof']):
                return False

            last_block = block
            current_index += 1

        return True

    def resolve_conflicts(self):
        new_chain = None

        max_length = len(self.chain)

        for node in self.nodes:
            response = requests.get('http://{}/chain'.format(node))

            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']

                # check whether the chain is the longest & valid
                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain

        if new_chain:
            self.chain = new_chain
            return True

        return False



# make new node
app = Flask(__name__)

# make unique address to this node
node_identifire = str(uuid4()).replace('-', '')

# make an instance of blockchain
blockchain = Blockchain()

@app.route('/transactoins/new', methods = ['POST'])
def new_transactions():
    return 'add new transactions'

@app.route('/chain', methods = ['GET'])
def full_chain():
    response = {
        'chain' : blockchain.chain,
        'length' : len(blockchain.chain),
        }
    return jsonify(response), 200

@app.route('/transactions/new', methods = ['POST'])
def new_transaction():
    values = request.get_json()

    required = ['sender', 'recipient', 'amount']
    if not all(k in values for k in required):
        return 'Missing values', 400

    index = blockchain.new_transaction(values['sender'], values['recipient'], values['amount'])

    response = {'message' : 'the transaction was add to {} block'.format(index)}
    return jsonify(response), 201

@app.route('/mine', methods = ['GET'])
def mine():
    last_block = blockchain.last_block
    last_proof = last_block['proof']
    proof = blockchain.proof_of_work(last_proof)

    # TODO transactionが無くてもmining自身のtransactionで採掘できてしまうバグ
    blockchain.new_transaction(
        sender = '0',
        recipient = node_identifire,
        amount = 1,
        )

    block = blockchain.new_block(proof)

    response = {
        'message' : 'mine new block',
        'index' : block['index'],
        'transactions' : block['transactions'],
        'proof' : block['proof'],
        'previous_hash' : block['previous_hash'],
        }
    return jsonify(response), 200

@app.route('/nodes/register', methods = ['POST'])
def register_node():
    values= request.get_json()

    nodes = values.get('nodes')
    if nodes is None:
        return '[Error] the list of invalid node', 400

    for node in nodes:
        block_chain.register_node(node)

    response = {
        'message' : 'new node is added',
        'total_nodes' : list(blockchain.nodes),
        }
    return jsonify(response), 201

@app.route('/nodes/resolve', methods = ['GET'])
def consensus():
    replaced = blockchain.resolve_conflicts()

    if replaced:
        response = {
            'message' : 'chain is replaced',
            'chain' : blockchain.chain,
            }
    else:
        response = {
            'message' : 'chain is checked',
            'chain' : blockchain.chain,
            }
        
    return jsonify(response), 200

# start a server using port 5000
if __name__ == '__main__':
    app.run(host = '0.0.0.0', port = 5000)
