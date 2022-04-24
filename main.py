from flask import Flask
from flask import request
import json
import random
import config


app = Flask(__name__)


def gen_enumirate_text(counters:list) -> str:
    length = len(counters)
    if length < 2:
        return counters[0]
    if length < 3:
        return counters[0] + ' и ' + counters[1]
    else:
        return ", ".join(counters [:length - 2]) + ' и ' + counters[length - 1]

class UserInfo(object):
    def __init__(self, cards:dict={}, hidden_cards:dict={},
    json_load:dict={}
    ):
        if json_load == {}:
            self.cards = cards
            self.hidden_cards = hidden_cards
        else:
            self.cards = json_load['cards']
            self.hidden_cards = json_load['hidden_cards']

    def to_json(self):
        res = {}
        res['cards'] = self.cards
        res['hidden_cards'] = self.hidden_cards
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
    def __init__(self, stage, users_play, catastrophe, space_on_bunker=0, current_user_index=0, current_game_round=0, voiting=False, current_user_moved=False):
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
        self.current_user_moved = current_user_moved
        self.space_on_bunker = space_on_bunker

    def get_object(self):
        resp = self.response
        resp['session_state'] = {
            'stage': self.stage,
            'users_play': {i:self.users_play[i].to_json() for i in self.users_play},
            'space_on_bunker': self.space_on_bunker,
            'catastrophe': self.catastrophe,
            'current_user_index': self.current_user_index,
            'current_game_round': self.current_game_round,
            'voiting': self.voiting,
            'current_user_moved': self.current_user_moved
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

    def next_user(self) -> tuple:
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

    response = Response(stage, users_play, 
    state['catastrophe'],
    state['space_on_bunker'],
    state['current_user_index'],
    state['current_game_round'],
    state['voiting'],
    state['current_user_moved'])

    #tests 
    if command_tokens[0] == 'tts':
        text_to_play = original_text [len(command_tokens[0]):]
        return response.play_message(text_to_play, text_to_play)

    if u_request['markup']['dangerous_context']:
        return response.play_message('Не хочу вас понимать. Попробуйте говорить вежливее.')

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
            if len(response.users_play) < config.MIN_PLAYERS:
                return response.play_message(f'Для этой игры нужно минимум 4 игрока. Позовите кого-нибудь ещё и начните игру повторно.')
            response.space_on_bunker = response.users_play // 2
            response.set_new_stage('game')
            response.set_new_curr_user(
                random.randint(0, len(response.users_play) - 1))
            catastrophe = config.catastrophes[response.catastrophe]
            return response.play_message(f'Приступим к игре. Случилась катастрофа ' + catastrophe['name'] + '.\n' + catastrophe['description'] + '.\nНачинаем?',
                                         f'Приступим к игре. Случилась катастрофа ' +
                                         catastrophe['name'] + '. ' +
                                         catastrophe['description'] +
                                         '. Начинаем?'
                                         )
        if entities is not None:
            for item in entities:
                if item['type'] == config.TYPES_YANDEX_ENTITYES['FIO']:
                    info_names = item['value']
                    if 'first_name' in info_names:
                        users_play = response.get_users_play()
                        first_name = info_names['first_name']
                        if len(users_play) >= config.MAX_PLAYERS:
                            return response.play_message('Игроков уже максимальное количество. Дождитесь новой игры.')
                        if first_name in list(users_play):
                            return response.play_message('Такое имя уже есть! Выберите другое.')
                        users_play[first_name] = UserInfo(
                            {
                            'profession': random.choice(config.profession),
                            'health': random.choice(config.health),
                            'hobby':  random.choice(config.hobby),
                            'fear':  random.choice(config.fear),
                            'personality': random.choice(config.person),
                            'addition_info':  random.choice(config.inform),
                            'special_card':  random.choice(config.specialmove)
                            },
                            [{'профессия': 'profession'}, 
                            {'здоровье': 'health'}, 
                            {'хобби': 'hobby'}, 
                            {'страхи': 'fear'}, 
                            {'личные качества':'personality'},
                            {'дополнительная информация': 'addition_info'},
                            {'специальная': 'special_card'}]
                        )
                        response.set_new_users_play(users_play)
                        return response.play_message(
                            f'Отлично! Кто следующий?\nЕсли все игроки уже присоединились, скажите: "Алиса, мы готовы"',
                            f'Отлично! - Кто следующий? - - - Если все игроки присоединились, скажите: Алиса - - мы готовы')

    if stage == 'game':
        curr_user = response.get_user_by_index(response.current_user_index)
        user_name = curr_user["name"].capitalize()
        info = curr_user['info']
        if response.voiting:
            if command_tokens[1] in ['выбывает', 'вылетает', 'убывает', 'бывает', 'убивает', 'побывает']:
                name_kick = command_tokens[0]
                names = [i.capitalize() for i in list(response.users_play)]
                if name_kick in list(response.users_play):
                    response.users_play.pop(name_kick)
                    if response.space_on_bunker >= len(response.users_play):
                        pass#Конец игры
                    return response.play_message(f'Хорошо, {name_kick.capitalize()} выбывает')
                else:
                    names_kick = gen_enumirate_text(names)
                    return response.play_message(f'Такой игрок с нами не играет. С нами играют: {names_kick}', f'Такой игрок с нами не играет. С нами играют: {names_kick}')
        
        if command == 'я закончил':
            if not response.current_user_moved:
                return response.play_message('Вы не походили')
            
            response.current_user_moved = False
            
            next_user_index, is_next_round = response.next_user()
            if is_next_round and response.current_game_round > 1:
                response.voiting = True
                return response.play_message(f'Раунд завершился. Сейчас вам нужно решить, кто (один человек) не попадёт в бункер и озвучить мне его имя. Например: "Алиса, Дима выбывает"',
                                                'Раунд завершился. - Сейчас вам нужно решить, кто не попадёт в бункер и озвучить мне его имя. Например: "Алиса, Дима выбывает"')
            else:
                next_user = response.get_user_by_index(next_user_index)
                user_name = next_user["name"].capitalize()
                addition_text = ''
                cards = [list(i)[0] for i in next_user['info'].hidden_cards]
                hidden_cards_read = ", ".join(cards)
                rand_card = random.choice(cards)
                if 'profession' in [i[list(i)[0]] for i in next_user['info'].hidden_cards]:
                    addition_text += 'Скажите, когда будете готовы ходить.'
                else:
                    addition_text += f'Какую карточку характеристики открыть? {user_name}, можете открыть одну из карточек: {hidden_cards_read}.\nНапример скажите: "Алиса, открой карточку {rand_card}'
                return response.play_message(f'Хорошо! {user_name} ходит. {addition_text}', f'Хорошо! {user_name} ходит. {addition_text}')            
    
        card_name = 'профессия'
        is_profession = 'profession' in 'profession' in [i[list(i)[0]] for i in curr_user['info'].hidden_cards]
        if command_tokens[0] == 'открой' or is_profession:
            if True in [i in ['специальная', 'специальную'] for i in command_tokens]:
                special_card = info.cards['special_card']
                if special_card['type'] == 'voice':
                    return response.play_message(special_card['name'], special_card['name_tts'])
                elif special_card['type'] == 'plus_space_bunker':
                    response.space_on_bunker += 1
                    return response.play_message(special_card['name'], special_card['name_tts'])
                    
                elif special_card['type'] == 'heal':
                    pass
                elif special_card['type'] == 'del_space_bunker':
                    response.space_on_bunker -= 1
                    return response.play_message(special_card['name'], special_card['name_tts'])
                
                elif special_card['type'] == 'fake_profession':
                    pass
                elif special_card['type'] == 'bad_tablet':
                    pass
                elif special_card['type'] == 'plan_b':
                    pass
                elif special_card['type'] == 'ineed_info':
                    pass
                elif special_card['type'] == 'steal':
                    pass
                elif special_card['type'] == 'radomise_all':
                    pass
                elif special_card['type'] == 'diverse':
                    pass
                elif special_card['type'] == 'replace_info':
                    pass
                elif special_card['type'] == 'replace_profession':
                    pass
                elif special_card['type'] == 'replace_health':
                    pass
                elif special_card['type'] == 'good_tablet':
                    pass 
            else:
                response.current_user_moved = True
                card_name = command_tokens[2] if not is_profession else 'профессия'
                opened_card = info.open_card(card_name)
                if opened_card is None:
                    return response.play_message('Извините, но карточка уже открыта.')
                card_key = opened_card['key']
                response.replace_user_info(response.current_user_index, info)

                
                if card_key == 'profession':
                    return response.play_message(
                        f'{user_name}, Ваша профессия — {info.cards["profession"]["name"]}. Как закончите аргументацию, сообщите мне.\nНапример: "Алиса, я закончил".',
                        f'{user_name}, - ваша профессия - {info.cards["profession"]["name_tts"]}. Как закончите аргументацию - сообщите мне. Например: - Алиса, - я закончил'
                    )
                elif card_key == 'health':
                    return response.play_message(
                        f'{user_name}, на Вашей карточке здоровья написано: {info.cards["health"]["name"]}. Как закончите аргументацию, скажите об этом мне.\nНапример: "Алиса, я закончил".',
                        f'{user_name}, - на Вашей карточке здоровья написано: - {info.cards["health"]["name"]}. Как закончите аргументацию - скажите об этом мне. Например: - Алиса, - я закончил.'   
                    )
                elif card_key == 'hobby':
                    return response.play_message(
                        f'{user_name}, на Вашей карточке хобби написано: {info.cards["hobby"]["name"]}. После агрументации сообщите мне о том, что Вы закончили.\nНапример, "Алиса, я закончил".',
                        f'{user_name}, - на Вашей карточке хобби написано: - {info.cards["hobby"]["name"]}. После агрументации сообщите мне о том - что Вы закончили. Например: - Алиса, - я закончил.'
                    )
                elif card_key == 'fear':
                    return response.play_message(
                        f'{user_name}, на Вашей карточке страха написано: {info.cards["fear"]["name"]}. Как закончите аргументацию, скажите об этом мне.\nНапример: "Алиса, я закончил".',
                        f'{user_name}, - на Вашей карточке страха написано: - {info.cards["fear"]["name"]}. Как закончите аргументацию - скажите об этом мне. Например: - Алиса, - я закончил.'
                    )
                elif card_key == 'personality':
                    return response.play_message(
                        f'{user_name}, на Вашей карточке личных качеств написано: {info.cards["personality"]["name"]}. Как закончите аргументацию, скажите об этом мне.\nНапример: "Алиса, я закончил".',
                        f'{user_name}, - на Вашей карточке личных качеств написано: - {info.cards["personality"]["name"]}. Как закончите аргументацию - скажите об этом мне. Например: - Алиса, - я закончил.'   
                    )
                elif card_key == 'addition_info':
                    return response.play_message(
                        f'{user_name}, на Вашей карточке дополнительной информации написано: {info.cards["addition_info"]["name"]}. После агрументации, сообщите мне о том, что Вы закончили.\nНапример, "Алиса, я закончил".',
                        f'{user_name}, - на Вашей карточке дополнительной информации написано: - {info.cards["addition_info"]["name"]}. После агрументации сообщите мне о том - что Вы закончили. Например: - Алиса, - я закончил.'
                    )
            

    return response.play_incorrect()


if __name__ == '__main__':
    app.run(port=3020, debug=True)
