from flask import Flask
from flask import request
import json

app = Flask(__name__)

default_response = {
        'version': '1.0',
        'response': {
            'end_session': False
        }
    }

@app.route('/handler', methods=['POST', 'GET'])
def main():
    data = json.loads(request.data)
    print(request.args.to_dict())
    print(data)
    response = default_response.copy()
    body = {
        'text': 'У вас получилось!',
        "tts": "<speaker audio=\"alice-sounds-game-win-1.opus\"> У вас получилось!"
    }
    response['response'].update(body)
    
    return response


if __name__ == '__main__':
    app.run(port=3020, debug=True)
    