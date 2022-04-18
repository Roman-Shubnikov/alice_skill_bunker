from config import default_messages


def play_message(response, text, tts) -> dict:
    body = {
        'text': text,
        'tts': tts
    }
    return play_message_body(response, body)

def play_message_body(response, body) -> dict:

    response['response'].update(body)

    return response

def tts_sound_formater(sound_name, text) -> str:
    return f'<speaker audio="{sound_name}"> {text}'

def play_incorrect(response) -> dict:
    return play_message_body(response, default_messages['incorrect'])