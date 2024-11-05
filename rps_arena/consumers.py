import json
from channels.generic.websocket import AsyncWebsocketConsumer

class GameConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f"game_{self.room_name}"
        
        # Initialize room-specific users and choices
        self.users = {}
        self.choices = {}
        
        # Add the current user to the room's user list
        user_id = self.scope['user'].id
        self.users[user_id] = self.scope['user']
        
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        print(f"User connected: {user_id}. Total users in room: {len(self.users)}")
        
        await self.accept()
        
    async def disconnect(self, close_code):
        user_id = self.scope['user'].id
        if user_id in self.users:
            del self.users[user_id]  # Remove the user from the room's user list
        
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
        print(f"User disconnected: {user_id}. Total users in room: {len(self.users)}")

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        choice = text_data_json['message']
        user = self.scope['user'].id
        
        # Record the choice if not already made
        if user not in self.choices:
            self.choices[user] = choice

        # Check if both players have made their choice
        if len(self.choices) == 2:
            message = self.game_decide()
        
            await self.channel_layer.group_send(
                self.room_group_name,
                {
                    'type': 'game_message',
                    'message': message
                }
            )
            
            # Clear choices after the game round
            self.choices.clear()

    async def game_message(self, event):
        message = event['message']
        await self.send(text_data=json.dumps({'message': message}))

    def game_decide(self):
        user1, user2 = list(self.choices.keys())
        choice1 = self.choices[user1]
        choice2 = self.choices[user2]

        if choice1 == choice2:
            return "It's a draw!"
        elif (choice1 == 'rock' and choice2 == 'scissors') or \
             (choice1 == 'scissors' and choice2 == 'paper') or \
             (choice1 == 'paper' and choice2 == 'rock'):
            return f'User {user1} won with {choice1} against {choice2}!'
        else:
            return f'User {user2} won with {choice2} against {choice1}!'
