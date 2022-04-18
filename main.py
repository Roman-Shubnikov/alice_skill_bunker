from calendar import c
from click import command
from flask import Flask
from flask import request
import json
import random
import config


app = Flask(__name__)
def get_default_response() -> dict:
    default_response = {
        'version': '1.0',
        'response': {
            'end_session': False
        }
    }
    return default_response


class Response(object):
    def __init__(self, stage, users_play, catastrophe, current_user_index=0):
        self.response = {
            'version': '1.0',
            'response': {
                'end_session': False
            }
        }
        self.stage = stage
        self.users_play = users_play
        self.catastrophe = catastrophe
    
    def get_object(self):
        resp = self.response
        resp['session_state'] = {
            'stage': self.stage,
            'users_play': self.users_play,
            'catastrophe': self.catastrophe,
            'current_user_index': self.current_user_index,
        }
        return resp

    def play_message(self, text, tts='') -> dict:
        body = {
            'text': text,
            'tts': tts
        }
        return self.play_message_body(body)

    def play_message_body(self, body) -> dict:

        self.response['response'].update(body)

        return self.get_object()
    def get_custom_message_for_pattern(self, pattern, add_text='', add_tts='') -> dict:
        message = pattern.copy()
        message['text'] += add_text
        message['tts'] += add_tts
        return self.play_message_body(message)

    def get_rules(self, text='', tts='') -> dict:
        return self.get_custom_message_for_pattern(config.default_messages['rules'], text, tts)

    def play_incorrect(self) -> dict:
        return self.play_message_body(config.default_messages['incorrect'])

    def next_user(self) -> dict:
        index_last_user = len(self.users_play) - 1
        if self.current_user_index + 1 > index_last_user: 
            self.current_user_index = 0
        else:
            self.current_user_index += 1
        return self.current_user_index
        
    def get_user_by_index(self, index) -> dict:
        name = self.users_play.keys()[index]
        return {'name': name, 'info': self.users_play[name]}

    def set_new_stage(self, stage):
        self.stage = stage
    def set_new_users_play(self, users_play):
        self.users_play = users_play
    def set_new_catastrophe(self, catastrophe):
        self.catastrophe = catastrophe
    def set_new_curr_user(self, current_user_index):
        self.current_user_index = current_user_index
    def get_users_play(self):
        return self.users_play

@app.route('/handler', methods=['POST', 'GET'])
def main():
    data = json.loads(request.data)
    print(data)
    session = data['session']
    user_obj = session['user'] if 'user' in session else None
    user_id = user_obj['user_id'] if user_obj else None
    # if user_id is not None:
    #     sql.query('INSERT IGNORE INTO users (uid) VALUES (%s)', (user_id))
    if session['new']:
        response = Response('approve_hello', {}, random.choice([i for i in range(0, len(config.catastrophes) - 1)]))
        return response.play_message_body(config.default_messages['hello'])

    state = data['state']['session']
    stage = state['stage']
    users_play = state['users_play']

    u_request = data['request']
    command = u_request['command']
    entities = u_request['nlu']['entities'] if 'nlu' in u_request and 'entities' in u_request['nlu'] else None

    response = Response(stage, users_play, state['catastrophe'])

    if 'повтори правила' in command:
        return response.get_rules()

    if stage == 'approve_hello':
        if command in config.approve_phrases:
            response.set_new_stage('approve_rules')
            return response.get_rules('Начинаем?', 'Начинаем?')

    if stage == 'approve_rules':
        if 'повтори' in command:
            return response.get_rules('Начинаем?', 'Начинаем?')
        if 'нет' in command:
            return response.play_message_body(config.default_messages['rules_repeat'])
        if command in config.approve_phrases:
            response.set_new_stage('users_registration')
            return response.play_message_body(config.default_messages['presentation_first_player'])

    if stage == 'users_registration':
        if 'повтори' in command:
            return response.play_message_body(config.default_messages['presentation_first_player'])
        if command in config.approve_phrases:
            response.set_new_stage('start_game')
            response.set_new_curr_user(random.randint(0, len(response.users_play) - 1))
            catastrophe = config.catastrophes[response.catastrophe]
            return response.play_message(f'Приступим к игре. Случилась катастрофа ' + catastrophe['name'] + '. ' + catastrophe['description'] + '. Начинаем?',
                f'Приступим к игре. Случилась катастрофа ' + catastrophe['name'] + '. ' + catastrophe['description'] + '. Начинаем?',
            )
        if entities is not None:
            for item in entities:
                if item['type'] == config.TYPES_YANDEX_ENTITYES['FIO']:
                    info_names = item['value']
                    if 'first_name' in info_names:
                        users_play = response.get_users_play()
                        first_name = info_names['first_name']
                        if first_name in users_play.keys():
                            return response.play_message('Такое имя уже есть! Выберите другое')

                        users_play[first_name] = {
                            'healh': {},
                            'hobby': '',
                            'scare': '',
                            'addition_info': '',
                            'special_card': '',
                            'hidden_cards': ['healh', 'hobby', 'scare', 'addition_info', 'special_card'],
                        }
                        response.set_new_users_play(users_play)
                        return response.play_message(
                        f'Отлично, {first_name.capitalize()}! Кто следующий? Если все игроки уже присоединились, скажите: "Алиса, мы готовы"',
                        f'Отлично {first_name}! Кто следующий? Если все игроки уже присоединились, скажите: "Алиса, мы готовы"')

        if stage == 'start_game':
            curr_user = response.get_user_by_index(response.current_user_index)
            

    return response.play_incorrect()
    
    


if __name__ == '__main__':
    app.run(port=3020, debug=True)
    