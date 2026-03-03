from extensions import socketio
from flask_socketio import emit, join_room, leave_room


def init_socket_events():
    @socketio.on('connect')
    def on_connect():
        print('[SOCKET] Client connected')

    @socketio.on('disconnect')
    def on_disconnect():
        print('[SOCKET] Client disconnected')

    @socketio.on('join_queue_room')
    def on_join(data):
        room = data.get('room')
        if room:
            join_room(room)
            emit('joined', {'room': room})

    @socketio.on('leave_queue_room')
    def on_leave(data):
        room = data.get('room')
        if room:
            leave_room(room)