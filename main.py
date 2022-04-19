from tkinter import E
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


class UserInfo(object):
    def __init__(self, cards:dict={}, voites=0, hidden_cards:dict={},
    json_load:dict={}
    ):
        if json_load == {}:
            self.cards = cards
            self.hidden_cards = hidden_cards
            self.voites = voites
        else:
            self.cards = json_load['cards']
            self.hidden_cards = json_load['hidden_cards']
            self.voites = json_load['voites']

    def to_json(self):
        res = {}
        res['cards'] = self.cards
        res['hidden_cards'] = self.hidden_cards
        res['voites'] = self.voites
        return res

    def get_hidden_cards(self):
        return self.hidden_cards

    def open_card(self, card_name):
        curr_card_ind, en_name = None, None
        for i, card in enumerate(self.hidden_cards):
            card_key = list(card)[0]
            if card_key == card_name:
                curr_card_ind, en_name = i, card[card_key]
                break
        if curr_card_ind is not None:
            self.hidden_cards.pop(curr_card_ind)
            return {'cards': self.hidden_cards, 'key': en_name}
        else:
            return None

class Response(object):
    def __init__(self, stage, users_play, catastrophe, current_user_index=0, current_game_round=0, voiting=False, voiting_position=0):
        self.response = {
            'version': '1.0',
            'response': {
                'end_session': False
            }
        }
        self.stage = stage
        self.users_play = {}
        for user in users_play.keys():
            self.users_play[user] = UserInfo(json_load=users_play[user])

        self.catastrophe = catastrophe
        self.current_user_index = current_user_index
        self.current_game_round = current_game_round
        self.voiting = voiting
        self.voiting_position = voiting_position

    def get_object(self):
        resp = self.response
        resp['session_state'] = {
            'stage': self.stage,
            'users_play': {i:self.users_play[i].to_json() for i in self.users_play},
            'catastrophe': self.catastrophe,
            'current_user_index': self.current_user_index,
            'current_game_round': self.current_game_round,
            'voiting': self.voiting,
            'voiting_position': self.voiting_position
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
        is_next_round = False
        if self.current_user_index + 1 > index_last_user:
            self.current_user_index = 0
            self.current_game_round += 1
            is_next_round = True
        else:
            self.current_user_index += 1
        return self.current_user_index, is_next_round

    def get_next_user_index(self):
        index_last_user = len(self.users_play) - 1
        if self.current_user_index + 1 > index_last_user:
            return 0
        else:
            return self.current_user_index + 1
    def get_user_by_index(self, index) -> dict:
        name = list(self.users_play)[index]
        return {'name': name, 'info': self.users_play[name]}

    def replace_user_info(self, index, user_info: UserInfo) -> bool:
        name = list(self.users_play)[index]
        self.users_play[name] = user_info

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
        response = Response('approve_hello', {}, random.choice(
            [i for i in range(0, len(config.catastrophes) - 1)]))
        return response.play_message_body(config.default_messages['hello'])

    state = data['state']['session']
    stage = state['stage']
    users_play = state['users_play']

    u_request = data['request']
    command = u_request['command']
    original_text = u_request['original_utterance']
    command_tokens = u_request['nlu']['tokens']
    entities = u_request['nlu']['entities'] if 'nlu' in u_request and 'entities' in u_request['nlu'] else None

    response = Response(stage, users_play, state['catastrophe'])

    #tests 
    if command_tokens[0] == 'tts':
        text_to_play = original_text [len(command_tokens[0]):]
        return response.play_message(text_to_play, text_to_play)

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
            response.set_new_stage('game')
            response.set_new_curr_user(
                random.randint(0, len(response.users_play) - 1))
            catastrophe = config.catastrophes[response.catastrophe]
            return response.play_message(f'Приступим к игре. Случилась катастрофа ' + catastrophe['name'] + '. ' + catastrophe['description'] + '. Начинаем?',
                                         f'Приступим к игре. Случилась катастрофа ' +
                                         catastrophe['name'] + '. ' +
                                         catastrophe['description'] +
                                         '. Начинаем?',
                                         )
        if entities is not None:
            for item in entities:
                if item['type'] == config.TYPES_YANDEX_ENTITYES['FIO']:
                    info_names = item['value']
                    if 'first_name' in info_names:
                        users_play = response.get_users_play()
                        first_name = info_names['first_name']
                        if first_name in list(users_play):
                            return response.play_message('Такое имя уже есть! Выберите другое.')

                        users_play[first_name] = UserInfo(
                            {
                            'profession': random.choice(config.profession),
                            'healh': random.choice(config.health),
                            'hobby':  random.choice(config.hobby),
                            'fear':  random.choice(config.fear),
                            'addition_info':  random.choice(config.inform),
                            'special_card':  random.choice(config.specialmove)
                            },
                            [{'профессия': 'profession'}, 
                            {'здоровье': 'health'}, 
                            {'хобби': 'hobby'}, 
                            {'страхи': 'fear'}, 
                            {'дополнительная информация': 'addition_info'},
                            {'специальная': 'special_card'}]
                        )
                        response.set_new_users_play(users_play)
                        return response.play_message(
                            f'Отлично, {first_name.capitalize()}! Кто следующий?\nЕсли все игроки уже присоединились, скажите: "Алиса, мы готовы"',
                            f'Отлично {first_name}! Кто следующий? Если все игроки уже присоединились, скажите: Алиса мы готовы')

    if stage == 'game':
        curr_user = response.get_user_by_index(response.current_user_index)
        info = curr_user['info']
        if response.voiting:
            if command_tokens[0] == 'убери':
                name_kick = command_tokens[1]
                names = list(response.users_play)
                if name_kick in names:
                    next_user_name = list(response.users_play)[response.get_next_user_index()].capitalize()
                    if response.voiting_position == response.get_next_user_index():
                        voiting_list = {}
                        for user in users_play:
                            u_count = response.users_play[user]['voites']
                            voiting_list[u_count] = user
                        max_voites = max(list(voiting_list))
                        kick_user_name = voiting_list[max_voites]
                        response.users_play.pop(kick_user_name)
                        user_question = f'По итогам голосования выбывает {kick_user_name}. Не расстраивайся! Выйграешь в другой раз. '
                        if len(response.users_play) == 1:
                            pass
                        #     name_winner = list(response.users_play)[0]
                        #     user_question += "Поздравляем! Игра закончилась. Победил {}"
                    else:
                        user_question = f'Теперь очередь следующего. {next_user_name}'
                    return response.play_message(f'Хорошо, {name_kick} получил уже {response.users_play[name_kick].voites} голосов За. {user_question}')
                else:
                    return response.play_message(f'Такой игрок с нами не играет. С нами играют: {", ".join(names)}')
        if command == 'я закончил':
            if response.current_game_round > 0:
                cards = list(info.hidden_cards)
                hidden_cards_read = ", ".join(cards)
                rand_card = random.choice(cards)
                return response.play_message(f'Вы можете открыть одну из карточек: {hidden_cards_read}.\nНапример скажите: "Алиса, открой карточку {rand_card}"')
                
        if command == 'я закончил' or len(list(info.hidden_cards)) == 0:
            next_index = is_next_round = response.next_user()
            if is_next_round and response.current_game_round > 1:
                response.voiting = True
                response.voiting_position = next_index
                rand_user = random.choice(list(response.users_play))
                starting_name = list(response.users_play)[response.current_user_index].capitalize()
                return response.play_message(f'Проведём голосование кого надо оставить, а кого убрать. Я по очереди буду вас спрашивать, кого выгнать, а вы мне ответите: "Алиса, убери {rand_user.capitalize()}. Начинает - {starting_name}"')
        
        card_name = 'профессия'
        if command_tokens[0] == 'открой':
            card_name = command_tokens[1]

        if 'profession' in info.cards['profession']:
            card_name = 'профессия'

        opened_card = info.open_card(card_name)
        if opened_card is None:
            pass
            # Извините карточка открыфть
        card_key = opened_card['key']
        response.replace_user_info(response.current_user_index, info)

        if card_key == 'profession':
            
            return response.play_message(
                f'{curr_user["name"]}, Ваша профессия — {info.cards["profession"]["name"]}. Как закончите аргументацию, сообщите мне.\nНапример: "Алиса, я закончил".',
                f'{curr_user["name"]} ваша профессия - {info.cards["profession"]["name_tts"]}. Как закончите аргументацию сообщите мне. Например: Алиса, я закончил'
            )
        elif card_key == 'health':
            pass
            

    return response.play_incorrect()


if __name__ == '__main__':
    app.run(port=3020, debug=True)
